"""
Efficient and generic get next/previous tags for the Django template language,
using Alex Gaynor's excellent templatetag_sugar library.

The library can be found at: http://pypi.python.org/pypi/django-templatetag-sugar

Usage:

    {% load next_previous %}
    ...
    {% get_next in <queryset> after <object> as <next> %}
    {% get_previous in <queryset> before <object> as <previous> %}

Initially published here: https://gist.github.com/1004216
"""

from django import template
register = template.Library()

from templatetag_sugar.register import tag
from templatetag_sugar.parser import Constant, Variable, Name

from .utils import get_next_or_previous


@tag(register, [Constant("in"), Variable(), Constant("after"), Variable(), Constant("as"), Name()])
def get_next(context, queryset, item, asvar):
    context[asvar] = get_next_or_previous(queryset, item, next=True)

    return ""


@tag(register, [Constant("in"), Variable(), Constant("before"), Variable(), Constant("as"), Name()])
def get_previous(context, queryset, item, asvar):
    context[asvar] = get_next_or_previous(queryset, item, next=False)

    return ""
