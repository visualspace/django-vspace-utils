""" This is backported from Django GitHub repo #1126. """
from django.template.base import Library
from django.template.defaultfilters import stringfilter

from .utils import Truncator

register = Library()


@register.filter(is_safe=True)
@stringfilter
def truncatechars_html(value, arg):
    """
    Truncates HTML after a certain number of chars.

    Argument: Number of chars to truncate after.

    Newlines in the HTML are preserved.
    """
    try:
        length = int(arg)
    except ValueError: # invalid literal for int()
        return value # Fail silently.
    return Truncator(value).chars(length, html=True, truncate=' ...')
