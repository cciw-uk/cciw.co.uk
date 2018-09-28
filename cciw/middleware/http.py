

# TODO - work out if this is needed at all now we are on DigitalOcean
def webfaction_fixes(get_response):
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
    def middleware(request):
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
            request.is_secure = lambda: request.META['HTTP_X_FORWARDED_SSL'] in ['on', 'on,on']

        return get_response(request)
    return middleware
