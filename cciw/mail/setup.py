from django.core.urlresolvers import reverse

from .lists import EMAIL_LISTS
from .mailgun import create_route, list_routes, update_route


# See https://mailgun.com/app/routes
def setup_mailgun_routes():
    existing_routes = list_routes()['items']
    existing_d = {i['description']: i for i in existing_routes}

    def update_or_create(name, expression, action, priority=None):
        if name in existing_d:
            route = existing_d[name]
            update_route(route['id'],
                         name,
                         expression,
                         actions,
                         priority=priority)
        else:
            create_route(name,
                         expression,
                         actions,
                         priority=priority)

    for name, regex, func, perm_func in EMAIL_LISTS:
        pattern = regex.pattern

        expression = """match_recipient('{0}')""".format(pattern)
        domain = "https://www.cciw.co.uk"
        forwarding_url = domain + reverse("cciw-mailgun-incoming")
        actions = ["""forward("{0}")""".format(forwarding_url),
                   "stop()"]
        update_or_create(name, expression, actions, priority=5)
