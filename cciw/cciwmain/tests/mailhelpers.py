import cgi
import re
import urlparse

def url_to_path_and_query(url):
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    querydata_t = cgi.parse_qs(query)
    querydata = {}
    for key, val in querydata_t.items():
        querydata[key] = val[-1]
    return (path, querydata)

def read_email(email, regex):
    urlmatch = re.search(regex, email.body)
    assert urlmatch is not None, "No URL found in sent email"
    url = urlmatch.group()
    assert "http://www.cciw.co.uk/" in url
    path, querydata = url_to_path_and_query(url)
    return url, path, querydata
