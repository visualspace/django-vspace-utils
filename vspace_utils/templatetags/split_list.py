"""
Adapted from https://djangosnippets.org/snippets/889/

Usage: {% split_list list as new_list 2 %}
"""

from django.template import Library
register = Library()

from templatetag_sugar.register import tag
from templatetag_sugar.parser import Constant, Variable, Name

from .utils import split_sequence


@tag(register, [Variable(), Constant('as'), Name(), Variable()])
def split_list(context, ls, new_ls, columns):
    """ Parse template tag: {% split_list list as new_list 2 %}. """

    context[new_ls] = split_sequence(ls, int(columns))

    return u''
