from django.http import HttpResponseForbidden

from cciw.auth import is_wiki_user

class PrivateWiki(object):
    # Make the wiki restricted to logged in users only.  Djiki does not provide
    # this feature yet.
    def process_request(self, request):
        if request.path.startswith('/wiki/'):
            if not (hasattr(request, 'user') and
                    request.user.is_authenticated() and
                    is_wiki_user(request.user)):
                return HttpResponseForbidden("<h1>Forbidden</h1>"
                                             "<p>You must be logged in to use this.")

