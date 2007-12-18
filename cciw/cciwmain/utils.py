import datetime
import re
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse


def obfuscate_email(email):
    # TODO - use javascript write statements, with fallback
    safe_email = email.replace('@', ' <b>at</b> ').replace('.', ' <b>dot</b> ')
    return mark_safe("<span style='text-decoration: underline;'>%s</span>" % safe_email)

    
#    return mark_safe("<span style='text-decoration: underline;'>%s</span>" % email.replace('@', ' <b>at</b> ').replace('.', ' <b>dot</b> '))

member_username_re = re.compile(r'^[A-Za-z0-9_]{3,15}$')

def get_member_href(user_name):
    if not member_username_re.match(user_name):
        # This can get called from feeds, and we need to ensure
        # we don't generate a URL, as it will go nowhere (also causes problems 
        # with the feed framework and utf-8).  
        # Also, this can be called via bbcode, so we need to ensure
        # that we don't pass anything to urlresolvers.reverse that
        # will make it die.
        return u''
    else:
        return reverse('cciwmain.members.detail', kwargs={'user_name':user_name})


def get_member_link(user_name):
    user_name = user_name.strip()
    if user_name.startswith(u"'"):
        return user_name
    else:
        return mark_safe(u'<a title="Information about user \'%s\'" href="%s">%s</a>' % \
               (user_name, get_member_href(user_name), user_name))

def get_member_icon(user_name):
    from django.conf import settings
    user_name = user_name.strip()
    if user_name.startswith(u"'"): # dummy user
        return u''
    else:
        # We use content negotiation to get the right file i.e.
        # apache will add the right extension on for us.
        return u'<img src="%s" class="userIcon" alt="icon" />' % \
            (settings.SPECIAL_MEDIA_URL + settings.MEMBER_ICON_PATH + user_name)


def modified_query_string(request, dict, fragment=''):
    """Returns the query string represented by request, with key-value pairs
    in dict added or modified.  """
    qs = request.GET.copy()
    # NB can't use qs.update(dict) here
    for k,v in dict.items():
        qs[k] = v
    return request.path + '?' + qs.urlencode() + fragment
    
def strip_control_chars(text):
    for i in range(0,32):
        text = text.replace(chr(i), '')
    return text
    
def validate_xml(filename):
    from xml.sax import sax2exts
    from xml.dom.ext.reader import Sax2

    p = sax2exts.XMLValParserFactory.make_parser()
    reader = Sax2.Reader(parser=p)
    dom_object = reader.fromUri(filename)
    return True
   
def unslugify(slug):
    "Turns dashes and underscores into spaces and applies title casing"
    return slug.replace("-", " ").replace("_", " ").title()

_current_domain = None
def get_current_domain():
    global _current_domain
    if _current_domain is None:
        from django.contrib.sites.models import Site
        _current_domain = Site.objects.get_current().domain
    return _current_domain


class UseOnceLazyDict(object):
    """
    Returns a lazy, read-only dictionary for use in wrapping generic
    views.  This dictionary must be initialised with the function and
    arguments used to get the data.  When data is extracted, the function
    is called to get the data, but then forgetton again.
    """
    def __init__(self, func, args=(), kwargs={}):
        self.func, self.args, self.kwargs = func, args, kwargs

    # if __getitem__ needs to be implemented, then it will
    # need to get the data and cache it, and when the same piece of
    # data is requested a second time, all the cached data should
    # be dropped

    def items(self):
        return self._get_data().items()
    
    def _get_data(self):
        return self.func(*self.args, **self.kwargs)
