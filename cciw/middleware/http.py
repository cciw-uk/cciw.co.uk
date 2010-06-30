from django.http import HttpResponsePermanentRedirect

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

class ForceSSLMiddleware(object):
    """
    Middleware that performs redirects from HTTP to HTTPS.
    """
    # We need SESSION_COOKIE_SECURE = True to have any genuine security over
    # SSH.  But it is a global setting, so sessions won't work over
    # HTTP. Therefore need to force everything to be HTTPS.
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.is_secure():
            newurl = "https://%s%s" % (request.get_host(), request.get_full_path())
            return HttpResponsePermanentRedirect(newurl)

class ActAsProxy(object):
    """
    Allows us to use privoxy and a redirect from www.cciw.co.uk
    for the sake of demos
    """
    URLS = ["http://www.cciw.co.uk"]
    def process_request(self, request):
        for u in self.URLS:
            if request.path.startswith(u):
                request.path = request.path_info = request.environ['PATH_INFO'] = request.path[len(u):]
                return
