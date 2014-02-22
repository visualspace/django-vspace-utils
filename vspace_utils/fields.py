import logging
logger = logging.getLogger(__name__)

import datetime

# Note: we need dnspython for this to work
# Install with `pip install dnspython`
import dns.resolver
import dns.exception

from django import forms
from django.utils.translation import ugettext as _
from django.utils import dates


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


class SplitDateFormField(forms.MultiValueField):
    """
    Adopted from: https://github.com/redsolution/django-utilities

    You can specify minimal and maximum date with attributes from_date
    (default datetime.date(1930,01,01)) and till_date (default datetime.date.today),
    they must have date type or be callable object. Also you may reverse order
    of years with help of boolean attribute reverse (default False).

    If from_date=datetime.date(2007,01,01), till_date=datetime.date(2010,01,01)
    and reverse=False, then we obtain the sequence of years: 2007, 2008, 2009, 2010
    """
    EMPTY = [('', u'---')]
    DAYS = [(day, '%02d' % day) for day in xrange(1, 32)]
    MONTHS = [(month, dates.MONTHS[month]) for month in xrange(1, 13)]
    DEFAULT_FROM_YEAR = 1930

    def __init__(
        self, from_date=datetime.date(DEFAULT_FROM_YEAR, 01, 01),
        till_date=datetime.date.today, reverse=False, *args, **kwargs
    ):
        if callable(from_date):
            from_date = from_date()
        if callable(till_date):
            till_date = till_date()
        self.from_date = from_date
        self.till_date = till_date
        from_year = from_date.year
        till_year = till_date.year
        years = [(year, '%04d' % year) for year in xrange(
            till_year, from_year - 1, -1)]

        if reverse:
            years.reverse()

        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])

        kwargs['widget'] = self.widget_factory(years)

        fields = (
            forms.ChoiceField(choices=self.DAYS),
            forms.ChoiceField(choices=self.MONTHS),
            forms.ChoiceField(choices=years),
        )

        super(SplitDateFormField, self).__init__(fields, *args, **kwargs)

    def compress(self, value_list):
        error_messages = forms.SplitDateTimeField.default_error_messages

        if value_list:
            for value in value_list:
                if value in forms.fields.EMPTY_VALUES:
                    raise forms.ValidationError(['invalid_date'])

            kwargs = {
                'day': int(value_list[0]),
                'month': int(value_list[1]),
                'year': int(value_list[2]),
            }

            try:
                date = datetime.date(**kwargs)
                if date > self.till_date or date < self.from_date:
                    raise forms.ValidationError(error_messages['invalid_date'])
                else:
                    return date
            except ValueError:
                raise forms.ValidationError(error_messages['invalid_date'])

        return None

    @classmethod
    def widget_factory(cls, years):
        class SplitDateWidget(forms.MultiWidget):
            def __init__(self, attrs=None):
                widgets = (
                    forms.Select(attrs=None, choices=cls.EMPTY + cls.DAYS),
                    forms.Select(attrs=None, choices=cls.EMPTY + cls.MONTHS),
                    forms.Select(attrs=None, choices=cls.EMPTY + years),
                )
                super(SplitDateWidget, self).__init__(widgets, attrs)

            def decompress(self, value):
                if value:
                    return [value.day, value.month, value.year]
                return [None, None, None]

        return SplitDateWidget
