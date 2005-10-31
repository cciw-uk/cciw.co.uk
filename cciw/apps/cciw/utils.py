def obfuscate_email(email):
    # TODO - make into javascript linky thing?
    return email.replace('@', ' <b>at</b> ').replace('.', ' <b>dot</b> ')

def get_member_link(user_name):
    user_name = user_name.strip()
    if user_name.startswith("'"):
        return user_name
    else:
        return '<a title="information about user \'' + user_name + '\'" href="/members/' + user_name + '/">' + user_name + '</a>'
    
def modified_query_string(request, dict, fragment = ''):
    """Returns the query string represented by request, with key-value pairs
    in dict added or modified.  """
    qs = request.GET.copy()
    # NB can't use qs.update(dict) here
    for k,v in dict.items():
        qs[k] = v
    return request.path + '?' + qs.urlencode() + fragment
    
def strip_control_chars(text):
    for i in range(0,32):
        text = text.replace(chr(i),'')
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
