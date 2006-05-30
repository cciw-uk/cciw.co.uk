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


class ThisYear(object):
    """
    Class to get what year the website is currently on.  The website year is
    equal to the year of the last camp in the database, or the year 
    afterwards if that camp is in the past. It is implemented
    in this way to allow backwards compatibilty with code that
    expects THISYEAR to be a simple integer.  And for fun.
    """
    def __init__(self):
        self.timestamp = None
        self.year = 0
        
    def get_year(self):
        from cciw.cciwmain.models import Camp
        lastcamp = Camp.objects.order_by('-end_date')[0]
        if lastcamp.end_date <= datetime.date.today():
            self.year = lastcamp.year + 1
        else:
            self.year = lastcamp.year
        self.timestamp = datetime.datetime.now()
        
    def update(self):
        # update every hour
        if self.timestamp is None or \
           (datetime.datetime.now() - self.timestamp).seconds > 3600:
            self.get_year()

    # TODO - better way of doing this lot? some metaclass magic I imagine
    def __str__(self):
        self.update()
        return str(self.year)
    
    __repr__ = __str__

    def __cmp__(self, other):
        self.update()
        return cmp(self.year, other)

    def __add__(self, other):
        self.update()
        return self.year + other

    def __sub__(self, other):
        self.update()
        return self.year - other

    def __int__(self):
        self.update()
        return self.year
