import re
import unicodedata
import string

from django.db.models import Q
from django.db.models.sql.query import get_order_dir

from django.utils.functional import allow_lazy, SimpleLazyObject
from django.utils.encoding import force_text
from django.utils.translation import pgettext

# Set up regular expressions
re_words = re.compile(r'&.*?;|<.*?>|(\w[\w-]*)', re.U|re.S)
re_tag = re.compile(r'<(/)?([^ ]+?)(?: (/)| .*?)?>', re.S)


def get_next_or_previous(qs, item, next=True):
    """
    Get the next or previous object in the queryset, with regards to the
    item specified.
    """
    # If we want the previous object, reverse the default ordering
    if next:
        default_ordering = 'ASC'
    else:
        default_ordering = 'DESC'

    # First, determine the ordering. This code is from get_ordering() in
    # django.db.sql.compiler
    if qs.query.extra_order_by:
        ordering = qs.query.extra_order_by
    elif not qs.query.default_ordering:
        ordering = qs.query.order_by
    else:
        ordering = qs.query.order_by or qs.query.model._meta.ordering

    assert not ordering == '?', 'This makes no sense for random ordering.'

    query_filter = None
    for field in ordering:
        item_value = getattr(item, field)

        # Account for possible reverse ordering
        field, direction = get_order_dir(field, default_ordering)

        # Either make sure we filter increased values or lesser values
        # depending on the sort order
        if direction == 'ASC':
            filter_dict = {'%s__gt' % field: item_value}
        else:
            filter_dict = {'%s__lt' % field: item_value}

        # Make sure we nicely or the conditions for the queryset
        if query_filter:
            query_filter = query_filter | Q(**filter_dict)
        else:
            query_filter = Q(**filter_dict)

    # Reverse the order if we're looking for previous items
    if default_ordering == 'DESC':
        qs = qs.reverse()

    # Filter the queryset
    qs = qs.filter(query_filter)

    # Return either the next/previous item or None if not existent
    try:
        return qs[0]
    except IndexError:
        return None


class Truncator(SimpleLazyObject):
    """
    An object used to truncate text, either by characters or words.
    """
    def __init__(self, text):
        super(Truncator, self).__init__(lambda: force_text(text))

    def add_truncation_text(self, text, truncate=None):
        if truncate is None:
            truncate = pgettext(
                'String to return when truncating text',
                '%(truncated_text)s...')
        truncate = force_text(truncate)
        if '%(truncated_text)s' in truncate:
            return truncate % {'truncated_text': text}
        # The truncation text didn't contain the %(truncated_text)s string
        # replacement argument so just append it to the text.
        if text.endswith(truncate):
            # But don't append the truncation text if the current text already
            # ends in this.
            return text
        return '%s%s' % (text, truncate)

    def chars(self, num, truncate=None, html=False, whole_words=False):
        """
        Returns the text truncated to be no longer than the specified number
        of characters.

        Takes an optional argument of what should be used to notify that the
        string has been truncated, defaulting to a translatable string of an
        ellipsis (...).

        If whole_word=True, truncation only truncates at word boundaries.
        """
        length = int(num)
        text = unicodedata.normalize('NFC', self._wrapped)

        # Calculate the length to truncate to (max length - end_text length)
        truncate_len = length
        for char in self.add_truncation_text('', truncate):
            if not unicodedata.combining(char):
                truncate_len -= 1
                if truncate_len == 0:
                    break
        if html:
            return self._html_chars(truncate_len, truncate, text, whole_words)
        return self._text_chars(length, truncate, text, whole_words)
    chars = allow_lazy(chars)

    def _text_chars(self, length, truncate, text, whole_words):
        """
        Truncates a string after a certain number of chars.
        """
        s_len = 0
        end_index = None
        for i, char in enumerate(text):
            if unicodedata.combining(char):
                # Don't consider combining characters
                # as adding to the string length
                continue
            s_len += 1
            if end_index is None and s_len > length:
                end_index = i
            if s_len > length:
                truncated = text[:end_index or 0]

                if whole_words and not char.isspace():
                    # Current character is whitespace, find previous
                    # whole word
                    truncated = truncated.rsplit(' ', 1)[0]

                    # Remove trailing whitespace and punctuation
                    truncated = truncated.rstrip(string.whitespace + string.punctuation)

                # Return the truncated string
                return self.add_truncation_text(truncated, truncate)

        # Return the original string since no truncation was necessary
        return text

    def _html_chars(self, length, truncate, text, whole_words):
        """
        Truncates HTML to a certain number of chars (not counting tags and
        comments). Closes opened tags if they were correctly closed in the
        given HTML.

        Newlines in the HTML are preserved.
        """
        if length <= 0:
            return ''
        html4_singlets = (
            'br', 'col', 'link', 'base', 'img',
            'param', 'area', 'hr', 'input'
        )
        # Count non-HTML chars and keep note of open tags
        pos = 0
        end_text_pos = 0
        chars = 0
        open_tags = []
        text_length = len(text)
        while chars < length:
            if pos == text_length:
                break
            # Check for tag
            tag = re_tag.match(text, pos)
            if not tag or end_text_pos:
                # Don't worry about non tags or tags after our truncate point
                if not unicodedata.combining(text[pos]):
                    chars = chars + 1
                pos = pos + 1
                if chars == length:
                    end_text_pos = pos
                continue
            else:
                pos = tag.end(0)
            closing_tag, tagname, self_closing = tag.groups()
            # Element names are always case-insensitive
            tagname = tagname.lower()
            if self_closing or tagname in html4_singlets:
                pass
            elif closing_tag:
                # Check for match in open tags list
                try:
                    i = open_tags.index(tagname)
                except ValueError:
                    pass
                else:
                    # SGML: An end tag closes, back to the matching start tag,
                    # all unclosed intervening start tags with omitted end tags
                    open_tags = open_tags[i + 1:]
            else:
                # Add it to the start of the open tags list
                open_tags.insert(0, tagname)
        if chars < length:
            # Don't try to close tags if we don't need to truncate
            return text
        out = text[:end_text_pos]
        truncate_text = self.add_truncation_text('', truncate)
        if truncate_text:
            out += truncate_text
        # Close any tags still open
        for tag in open_tags:
            out += '</%s>' % tag
        # Return string
        return out

    def words(self, num, truncate=None, html=False):
        """
        Truncates a string after a certain number of words. Takes an optional
        argument of what should be used to notify that the string has been
        truncated, defaulting to ellipsis (...).
        """
        length = int(num)
        if html:
            return self._html_words(length, truncate)
        return self._text_words(length, truncate)
    words = allow_lazy(words)

    def _text_words(self, length, truncate):
        """
        Truncates a string after a certain number of words.

        Newlines in the string will be stripped.
        """
        words = self._wrapped.split()
        if len(words) > length:
            words = words[:length]
            return self.add_truncation_text(' '.join(words), truncate)
        return ' '.join(words)

    def _html_words(self, length, truncate):
        """
        Truncates HTML to a certain number of words (not counting tags and
        comments). Closes opened tags if they were correctly closed in the
        given HTML.

        Newlines in the HTML are preserved.
        """
        if length <= 0:
            return ''
        html4_singlets = (
            'br', 'col', 'link', 'base', 'img',
            'param', 'area', 'hr', 'input'
        )
        # Count non-HTML words and keep note of open tags
        pos = 0
        end_text_pos = 0
        words = 0
        open_tags = []
        while words <= length:
            m = re_words.search(self._wrapped, pos)
            if not m:
                # Checked through whole string
                break
            pos = m.end(0)
            if m.group(1):
                # It's an actual non-HTML word
                words += 1
                if words == length:
                    end_text_pos = pos
                continue
            # Check for tag
            tag = re_tag.match(m.group(0))
            if not tag or end_text_pos:
                # Don't worry about non tags or tags after our truncate point
                continue
            closing_tag, tagname, self_closing = tag.groups()
            # Element names are always case-insensitive
            tagname = tagname.lower()
            if self_closing or tagname in html4_singlets:
                pass
            elif closing_tag:
                # Check for match in open tags list
                try:
                    i = open_tags.index(tagname)
                except ValueError:
                    pass
                else:
                    # SGML: An end tag closes, back to the matching start tag,
                    # all unclosed intervening start tags with omitted end tags
                    open_tags = open_tags[i + 1:]
            else:
                # Add it to the start of the open tags list
                open_tags.insert(0, tagname)
        if words <= length:
            # Don't try to close tags if we don't need to truncate
            return self._wrapped
        out = self._wrapped[:end_text_pos]
        truncate_text = self.add_truncation_text('', truncate)
        if truncate_text:
            out += truncate_text
        # Close any tags still open
        for tag in open_tags:
            out += '</%s>' % tag
        # Return string
        return out
