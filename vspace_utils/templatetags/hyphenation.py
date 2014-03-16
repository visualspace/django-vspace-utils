"""
This template filter is meant to insert soft hyphens (&shy; entities) in text whever it can. For this is relies on a recent checkout of the PyHyphen interface to the hyphen-2.3 C library, which is also used by Mozilla and OpenOffice.org.

It takes two optional parameters: the language to hyphenate in and the minimum word length to consider for hyphenation. If no language is given, the default language from the settings file is used. The second parameter defaults to 5 characters.

Usage example:

{% load hyphenation %}
{{ object.text|hyphenate:"nl,7" }}
"""

import locale

from hyphen import Hyphenator, dictools

from django.utils.safestring import mark_safe
from django.utils.translation import get_language

from django import template
register = template.Library()


@register.filter
def hyphenate(value, arg=None, autoescape=None):
    # Default minimal length
    minlen = 6

    if arg:
        args = arg.split(u',')
        code = args[0]

        # Override minimal length, if specified
        if len(args) > 1:
            minlen = int(args[1])
    else:
        # No language specified, use Django's current
        code = get_language()

    # Normalize the locale code, ignoring a potential encoding suffix
    lang = locale.normalize(code).split('.')[0]

    # Make sure the proper language is installed
    if not dictools.is_installed(lang):
        dictools.install(lang)

    h = Hyphenator(lang)
    new = []
    for word in value.split(u' '):
        if len(word) > minlen and word.isalpha():
            new.append(u'&shy;'.join(h.syllables(word)))
        else:
            new.append(word)

    result = u' '.join(new)
    return mark_safe(result)
hyphenate.needs_autoescape = True
