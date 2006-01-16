from django.core import template
import bbcode

def bb2html(value):
    """Converts message board 'BB code'-like formatting into HTML"""
    return bbcode.bb2xhtml(value, True)
    
register = template.Library()
register.filter('bb2html', bb2html)

