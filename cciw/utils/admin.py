from .views import reroute_response


class RerouteResponseAdminMixin(object):
    """
    Admin mixin that allows a different return URL to
    be substituted using a '_return_to' query string parameter.
    """
    def conditional_reroute(self, request, main_response):
        response = reroute_response(request, default_to_close=False)
        if response is not None:
            return response
        return main_response

    def response_post_save_add(self, request, obj):
        return self.conditional_reroute(request,
                                        super(RerouteResponseAdminMixin, self).response_post_save_add(request, obj))

    def response_post_save_change(self, request, obj):
        return self.conditional_reroute(request,
                                        super(RerouteResponseAdminMixin, self).response_post_save_change(request, obj))
