import logging
logger = logging.getLogger(__name__)

# Note: we need dnspython for this to work
# Install with `pip install dnspython`
import dns.resolver
import dns.exception

from django import forms
from django.utils.translation import ugettext as _


class ValidatingEmailField(forms.EmailField):
    """
    Django EmailField which checks for MX records on the email domain.
    Requires dnspython to be installed.

    Initially published at: https://gist.github.com/876648
    """

    def clean(self, value):
        email = super(ValidatingEmailField, self).clean(value)

        domain = email.split('@')[1]

        # Make sure the domain exists
        try:
            logger.debug('Checking domain %s', domain)

            dns.resolver.query(domain, 'MX')

        except dns.exception.DNSException, e:
            logger.debug('Domain %s does not exist.', e)

            raise forms.ValidationError(_(
                u"The domain %s could not be found.") % domain
            )

        return email
