from .views import get_return_to_response


class ReturnToAdminMixin(object):
    """
    Admin mixin that allows a different return URL to
    be substituted using a '_return_to' query string parameter.
    """
    def conditional_redirect(self, request, main_response):
        redirect = get_return_to_response(request)
        if redirect is not None:
            return redirect
        return main_response

    def response_post_save_add(self, request, obj):
        return self.conditional_redirect(request,
                                         super(ReturnToAdminMixin, self).response_post_save_add(request, obj))

    def response_post_save_change(self, request, obj):
        return self.conditional_redirect(request,
                                         super(ReturnToAdminMixin, self).response_post_save_change(request, obj))
