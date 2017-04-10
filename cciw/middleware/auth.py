from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.html import escape
from django.utils.http import urlquote


def private_wiki(get_response):
    # Make the wiki restricted to logged in users only.  Djiki does not provide
    # this feature yet.
    def middleware(request):
        if request.path.startswith('/wiki/'):
            if not (hasattr(request, 'user') and
                    request.user.is_authenticated):
                return HttpResponseForbidden("<h1>Forbidden</h1>"
                                             "<p>You must be <a href='%s?next=%s'>logged in</a> to use this.</p>" %
                                             (settings.LOGIN_URL, escape(urlquote(request.get_full_path()))))
            if not request.user.is_wiki_user:
                return HttpResponseForbidden("<h1>Forbidden</h1>"
                                             "<p>You do not have permission to access the wiki.</p>")

        return get_response(request)

    return middleware
