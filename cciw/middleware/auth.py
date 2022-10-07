from urllib.parse import quote as urlquote

from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.html import escape

from ..utils.views import redirect_to_password_change_with_next


def private_wiki(get_response):
    # Make the wiki restricted to logged in users only.  Djiki does not provide
    # this feature yet.
    def middleware(request):
        if request.path.startswith("/wiki/"):
            if not (hasattr(request, "user") and request.user.is_authenticated):
                return HttpResponseForbidden(
                    "<h1>Forbidden</h1>"
                    "<p>You must be <a href='%s?next=%s'>logged in</a> to use this.</p>"
                    % (settings.LOGIN_URL, escape(urlquote(request.get_full_path())))
                )
            if not request.user.is_wiki_user:
                return HttpResponseForbidden(
                    "<h1>Forbidden</h1>" "<p>You do not have permission to access the wiki.</p>"
                )

        return get_response(request)

    return middleware


def bad_password_checks(get_response):
    def middleware(request):
        user = request.user
        if user.is_authenticated and user.bad_password:
            redirect_response = redirect_to_password_change_with_next(request)
            if redirect_response is not None:
                return redirect_response
        return get_response(request)

    return middleware
