import datetime

def obfuscate_email(email):
    # TODO - make into javascript linky thing?
    return email.replace('@', ' <b>at</b> ').replace('.', ' <b>dot</b> ')

def get_member_href(user_name):
    return '/members/' + user_name + '/'

def get_member_link(user_name):
    user_name = user_name.strip()
    if user_name.startswith("'"):
        return user_name
    else:
        return '<a title="Information about user \'' + user_name + \
           '\'" href="' + get_member_href(user_name) + '">' + user_name + '</a>'

def get_member_icon(user_name):
    from django.conf import settings
    user_name = user_name.strip()
    if user_name.startswith("'"): # dummy user
        return ''
    else:
        # We use content negotiation to get the right file i.e.
        # apache will add the right extension on for us.
        return '<img src="%s" class="userIcon" alt="icon" />' % \
            (settings.MEDIA_URL + settings.MEMBER_ICON_PATH + user_name)


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

def get_extract(utf8string, maxlength):
    u = utf8string.decode('UTF-8')
    if len(u) > maxlength:
        u = u[0:maxlength-3] + "..."
    return u.encode('UTF-8')
    
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
