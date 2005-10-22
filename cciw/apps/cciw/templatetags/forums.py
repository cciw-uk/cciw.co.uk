from django.core import template
import bbcode

def bb2html(value, _):
    """Converts message board 'BB code'-like formatting into HTML"""
    return bbcode.bb2xhtml(value, True)
    

template.register_filter('bb2html', bb2html, False)

