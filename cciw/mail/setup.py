from django.core.urlresolvers import reverse

from .lists import EMAIL_LISTS
from .mailgun import create_route, list_routes, update_route, update_webhook, create_webhook


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

    for e in EMAIL_LISTS:
        pattern = e.address_matcher.pattern
        expression = """match_recipient('{0}')""".format(pattern)
        domain = "https://www.cciw.co.uk"
        forwarding_url = domain + reverse("cciw-mailgun-incoming")
        actions = ["""forward("{0}")""".format(forwarding_url),
                   "stop()"]
        update_or_create(e.name, expression, actions, priority=5)


def setup_mailgun_webhooks():
    domain = "https://www.cciw.co.uk"
    webhook_bounce_url = domain + reverse("cciw-mailgun-bounce")
    try:
        create_webhook('bounce', webhook_bounce_url)
    except Exception:
        update_webhook('bounce', webhook_bounce_url)
