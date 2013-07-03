import platform
import re
import urllib
import urllib2
import urlparse

from os.path import splitext

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import filesizeformat

from django.core.validators import RegexValidator
from django.core.urlresolvers import resolve
from django.http import Http404
from django.utils.encoding import smart_unicode

try:
    from django.conf import settings
    URL_VALIDATOR_USER_AGENT = settings.URL_VALIDATOR_USER_AGENT
except ImportError:
    # It's OK if Django settings aren't configured.
    URL_VALIDATOR_USER_AGENT = 'Django (http://www.djangoproject.com/)'


class URLValidator(RegexValidator):
    """
    URLValidator with verify_exists still in there. Only to be used with
    trusted users. This is the original Django code.

    See: https://www.djangoproject.com/weblog/2011/sep/09/security-releases-issued/
    """
    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def __init__(self, verify_exists=False,
                 validator_user_agent=URL_VALIDATOR_USER_AGENT):
        super(URLValidator, self).__init__()
        self.verify_exists = verify_exists
        self.user_agent = validator_user_agent

    def __call__(self, value):
        try:
            super(URLValidator, self).__call__(value)
        except ValidationError, e:
            # Trivial case failed. Try for possible IDN domain
            if value:
                value = smart_unicode(value)
                scheme, netloc, path, query, fragment = urlparse.urlsplit(value)
                try:
                    netloc = netloc.encode('idna') # IDN -> ACE
                except UnicodeError: # invalid domain part
                    raise e
                url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
                super(URLValidator, self).__call__(url)
            else:
                raise
        else:
            url = value

        #This is deprecated and will be removed in a future release.
        if self.verify_exists:
            headers = {
                "Accept": "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
                "Accept-Language": "en-us,en;q=0.5",
                "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
                "Connection": "close",
                "User-Agent": self.user_agent,
            }
            url = url.encode('utf-8')
            # Quote characters from the unreserved set, refs #16812
            url = urllib.quote(url, "!*'();:@&=+$,/?#[]")
            broken_error = ValidationError(
                _(u'This URL appears to be a broken link.'), code='invalid_link')
            try:
                req = urllib2.Request(url, None, headers)
                req.get_method = lambda: 'HEAD'
                #Create an opener that does not support local file access
                opener = urllib2.OpenerDirector()

                #Don't follow redirects, but don't treat them as errors either
                error_nop = lambda *args, **kwargs: True
                http_error_processor = urllib2.HTTPErrorProcessor()
                http_error_processor.http_error_301 = error_nop
                http_error_processor.http_error_302 = error_nop
                http_error_processor.http_error_307 = error_nop

                handlers = [urllib2.UnknownHandler(),
                            urllib2.HTTPHandler(),
                            urllib2.HTTPDefaultErrorHandler(),
                            urllib2.FTPHandler(),
                            http_error_processor]
                try:
                    import ssl
                    handlers.append(urllib2.HTTPSHandler())
                except:
                    #Python isn't compiled with SSL support
                    pass
                map(opener.add_handler, handlers)
                if platform.python_version_tuple() >= (2, 6):
                    opener.open(req, timeout=10)
                else:
                    opener.open(req)
            except ValueError:
                raise ValidationError(_(u'Enter a valid URL.'), code='invalid')
            except: # urllib2.URLError, httplib.InvalidURL, etc.
                raise broken_error


class RelativeURLValidator(URLValidator):
    """
    Verifying validator which allows for relative URL's (within the current
    website). For use with trusted users only, due to known DoS-vector.

    Ref: https://www.djangoproject.com/weblog/2011/sep/09/security-releases-issued/
    """

    regex = re.compile(
        r'^((?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE) # host is optional, allow for relative URLs

    def __call__(self, value):
        try:
            # Attempt validation in the superclass: checks full-fledged URL's
            super(RelativeURLValidator, self).__call__(value)
        except ValidationError as e:
            if self.verify_exists:
                broken_error = ValidationError(
                    _(u'This URL appears to be a broken link.'),
                    code='invalid_link'
                )

                # Attempt local validation
                try:
                    resolve(value)
                except Http404:
                    raise broken_error

            # Re-raise original error
            raise e


class FileValidator(object):
    """
    Validator for files, checking the size, extension and mimetype.

    Initialization parameters:
        allowed_extensions: iterable with allowed file extensions
            ie. ('txt', 'doc')
        allowd_mimetypes: iterable with allowed mimetypes
            ie. ('image/png', )
        min_size: minimum number of bytes allowed
            ie. 100
        max_size: maximum number of bytes allowed
            ie. 24*1024*1024 for 24 MB

    Usage example::

        MyModel(models.Model):
            myfile = FileField(validators=FileValidator(max_size=24*1024*1024), ...)

    Initially published here: https://gist.github.com/1183767
    """

    extension_message = _("Extension '%(extension)s' not allowed. Allowed extensions are: '%(allowed_extensions)s.'")
    mime_message = _("MIME type '%(mimetype)s' is not valid. Allowed types are: %(allowed_mimetypes)s.")
    min_size_message = _('The current file %(size)s, which is too small. The minumum file size is %(allowed_size)s.')
    max_size_message = _('The current file %(size)s, which is too large. The maximum file size is %(allowed_size)s.')

    def __init__(self, *args, **kwargs):
        self.allowed_extensions = kwargs.pop('allowed_extensions', None)
        self.allowed_mimetypes = kwargs.pop('allowed_mimetypes', None)
        self.min_size = kwargs.pop('min_size', 0)
        self.max_size = kwargs.pop('max_size', None)

    def __call__(self, value):
        """
        Check the extension, content type and file size.
        """
        # Check the extension
        ext = splitext(value.name)[1][1:].lower()
        if self.allowed_extensions and not ext in self.allowed_extensions:
            message = self.extension_message % {
                'extension': ext,
                'allowed_extensions': ', '.join(self.allowed_extensions)
            }

            raise ValidationError(message)

        # Check the content type
        mimetype = value.file.content_type
        if self.allowed_mimetypes and not mimetype in self.allowed_mimetypes:
            message = self.mime_message % {
                'mimetype': mimetype,
                'allowed_mimetypes': ', '.join(self.allowed_mimetypes)
            }

            raise ValidationError(message)

        # Check the file size
        filesize = value.file._size
        if self.max_size and filesize > self.max_size:
            message = self.max_size_message % {
                'size': filesizeformat(filesize),
                'allowed_size': filesizeformat(self.max_size)
            }

            raise ValidationError(message)

        elif filesize < self.min_size:
            message = self.min_size_message % {
                'size': filesizeformat(filesize),
                'allowed_size': filesizeformat(self.min_size)
            }

            raise ValidationError(message)
