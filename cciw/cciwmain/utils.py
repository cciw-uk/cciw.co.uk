import datetime
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse


def obfuscate_email(email):
    # TODO - make into javascript linky thing?
    return "<span style='text-decoration: underline;'>%s</span>" % email.replace('@', ' <b>at</b> ').replace('.', ' <b>dot</b> ') 

def get_member_href(user_name):
    if user_name.startswith("'"):
        # This can get called from feeds, and we need to ensure
        # we don't generate a URL, as it will go nowhere (also causes problems 
        # with the feed framework and utf-8)
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
