
class WebFactionFixes(object):
    """
    Middleware that applies some fixes for people using
    the WebFaction hosting provider.  In particular:

    * sets 'REMOTE_ADDR' based on 'HTTP_X_FORWARDED_FOR', if the
      latter is set.

    * Monkey patches request.is_secure() to respect HTTP_X_FORWARDED_SSL.
      PLEASE NOTE that this is not reliable, since a user could set
      X-Forwarded-SSL manually and the main WebFaction Apache instance
      does not remove it, so it will appear to be a secure request
      when it is not.
    """
    def process_request(self, request):
        # Fix REMOTE_ADDR
        try:
            real_ip = request.META['HTTP_X_FORWARDED_FOR']
        except KeyError:
            pass
        else:
            # HTTP_X_FORWARDED_FOR can be a comma-separated list of IPs. The
            # client's IP will be the first one.
            real_ip = real_ip.split(",")[0].strip()
            request.META['REMOTE_ADDR'] = real_ip

        # Fix HTTPS
        if 'HTTP_X_FORWARDED_SSL' in request.META:
            request.is_secure = lambda: request.META['HTTP_X_FORWARDED_SSL'] == 'on'


class ActAsProxy(object):
    """
    When running a demo, and wanting to show the correct domain name, simply
    add this middleware and set 127.0.0.1:8000 as the proxy in the web
    browser.  If you need the browser to make requests to other domains, use
    privoxy and a redirect.
    """
    URLS = ["http://www.cciw.co.uk"]
    def process_request(self, request):
        for u in self.URLS:
            if request.path.startswith(u):
                request.path = request.path_info = request.environ['PATH_INFO'] = request.path[len(u):]
                return
