import logging
logger = logging.getLogger(__name__)

from django.utils.decorators import classonlymethod
from django.utils.functional import update_wrapper
from django.utils import translation
from django.utils.translation import get_language

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage

from django.template.loader import render_to_string

from django.contrib.sites.models import Site


class Listener(object):
    """
    Class-based listeners, based on Django's class-based generic views. Yay!

    Usage::

        class MySillyListener(Listener):
            def dispatch(self, sender, **kwargs):
                # DO SOMETHING
                pass

        funkysignal.connect(MySillyListener.as_view(), weak=False)
    """

    def __init__(self, **kwargs):
        """
        Constructor. Called in the URLconf; can contain helpful extra
        keyword arguments, and other things.
        """
        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    @classonlymethod
    def as_listener(cls, **initkwargs):
        """
        Main entry point for a sender-listener process.
        """
        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(u"You tried to pass in the %s method name as a "
                                u"keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError(u"%s() received an invalid keyword %r" % (
                    cls.__name__, key))

        def listener(sender, **kwargs):
            self = cls(**initkwargs)
            return self.dispatch(sender, **kwargs)

        # take name and docstring from class
        update_wrapper(listener, cls, updated=())

        # and possible attributes set by decorators
        update_wrapper(listener, cls.dispatch, assigned=())
        return listener

    def dispatch(self, sender, **kwargs):
        raise NotImplementedError('Sublcasses should implement this!')


class EmailingListener(Listener):
    """ Listener which sends out emails. """

    body_template_name = None
    subject_template_name = None

    def get_subject_template_names(self):
        """
        Returns a list of template names to be used for the request. Must return
        a list. May not be called if render_to_response is overridden.
        """
        if self.subject_template_name is None:
            raise ImproperlyConfigured(
                "TemplateResponseMixin requires either a definition of "
                "'template_name' or an implementation of 'get_template_names()'")
        else:
            return [self.subject_template_name]

    def get_body_template_names(self):
        """
        Returns a list of template names to be used for the request. Must return
        a list. May not be called if render_to_response is overridden.
        """
        if self.body_template_name is None:
            raise ImproperlyConfigured(
                "TemplateResponseMixin requires either a definition of "
                "'template_name' or an implementation of 'get_template_names()'")
        else:

            return [self.body_template_name]

    def get_context_data(self):
        """
        Context for the message template rendered. Defaults to sender, the
        current site object and kwargs.
        """

        current_site = Site.objects.get_current()

        context = {'sender': self.sender,
                   'site': current_site}

        context.update(self.kwargs)

        return context

    def get_recipients(self):
        """ Get recipients for the message. """
        raise NotImplementedError

    def get_sender(self):
        """
        Sender of the message, defaults to `None` which imples
        `DEFAULT_FROM_EMAIL`.
        """
        return None

    def create_message(self, context):
        """ Create an email message. """
        subject = render_to_string(self.get_subject_template_names(), context)
        # Clean the subject a bit for common errors (newlines!)
        subject = subject.strip().replace('\n', ' ')

        body = render_to_string(self.get_body_template_names(), context)
        recipients = self.get_recipients()
        sender = self.get_sender()

        email = EmailMessage(subject, body, sender, recipients)

        return email

    def handler(self, sender, **kwargs):
        """ Store sender and kwargs attributes on self. """

        self.sender = sender
        self.kwargs = kwargs

        context = self.get_context_data()

        message = self.create_message(context)

        message.send()


class TranslatedEmailingListener(EmailingListener):
    """ Email sending listener which switched locale before processing. """

    def get_language(self, sender, **kwargs):
        """ Return the language we should switch to. """
        raise NotImplementedError

    def handler(self, sender, **kwargs):
        old_language = get_language()

        language = self.get_language(sender, **kwargs)

        logger.debug('Changing to language %s for email submission', language)
        translation.activate(language)

        super(TranslatedEmailingListener, self).handler(sender, **kwargs)

        translation.activate(old_language)
