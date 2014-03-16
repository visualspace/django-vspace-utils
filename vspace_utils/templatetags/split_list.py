"""
Adapted from https://djangosnippets.org/snippets/889/

Usage: {% split_list list as new_list 2 %}
"""

from django.template import Library, Node, TemplateSyntaxError

register = Library()


class SplitListNode(Node):
    def __init__(self, list, cols, new_list):
        self.list, self.cols, self.new_list = list, cols, new_list

    def split_seq(self, list, cols=2):
        start = 0
        for i in xrange(cols):
            stop = start + len(list[i::cols])
            yield list[start:stop]
            start = stop

    def render(self, context):
        context[self.new_list] = self.split_seq(
            context[self.list], int(self.cols)
        )
        return ''


@register.tag
def split_list(parser, token):
    """Parse template tag: {% split_list list as new_list 2 %}"""

    bits = token.contents.split()

    if len(bits) != 5:
        raise TemplateSyntaxError("split_list list as new_list 2")

    if bits[2] != 'as':
        raise TemplateSyntaxError(
            "second argument to the split_list tag must be 'as'"
        )

    return SplitListNode(bits[1], bits[4], bits[3])
