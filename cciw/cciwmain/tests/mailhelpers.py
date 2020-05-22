import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunsplit


def url_to_path_and_query(url):
    scheme, netloc, path, params, query, fragment = urlparse(url)
    querydata_t = parse_qs(query)
    querydata = {}
    for key, val in querydata_t.items():
        querydata[key] = val[-1]
    return (path, querydata)


def read_email_url(email, regex):
    """
    Reads and parses a URL from an email
    """
    urlmatch = re.search(regex, email.body)
    assert urlmatch is not None, f"No URL matching {regex} found in sent email"
    url = urlmatch.group()
    path, querydata = url_to_path_and_query(url)
    return url, path, querydata


def path_and_query_to_url(path, querydata):
    return urlunsplit(('', '', path, urlencode(querydata), ''))
