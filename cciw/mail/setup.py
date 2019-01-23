from django.conf import settings
from django.urls import reverse

from .lists import EMAIL_LISTS
from .mailgun import create_route, create_webhook, list_routes, update_route, update_webhook

# See https://mailgun.com/app/routes


# In addition to the ones created here, which are routed through the website,
# there are simple forwarding addresses set up with the mailgun control panel.
def setup_mailgun_routes():
    existing_routes = list_routes()['items']
    existing_d = {i['description']: i for i in existing_routes}

    def update_or_create(name, expression, actions, priority=None):
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
        pattern = limit_pattern(e.address_matcher.pattern)
        expression = """match_recipient('{0}')""".format(pattern)
        forwarding_url = "https://" + settings.PRODUCTION_DOMAIN + reverse("cciw-mailgun-incoming")
        actions = ["""forward("{0}")""".format(forwarding_url),
                   "stop()"]
        update_or_create(e.name, expression, actions, priority=5)

    # Temporarily disabled the following - possibly mailgun's incoming
    # spam filter will deal with this
    # # Some incoming spam from @cciw.co.uk addresses. There is virtually no
    # # reason for a valid person to be using an @cciw.co.uk address, so we block
    # # this by adding a high priority rule.
    # update_or_create("From CCIW domain blocker",
    #                  r"""match_header("from", "@cciw\.co\.uk")""",
    #                  ["stop()"],
    #                  priority=0)


def setup_mailgun_webhooks():
    base_url = "https://" + settings.PRODUCTION_DOMAIN
    urls = [
        ('bounce', 'cciw-mailgun-bounce'),
    ]

    for webhook_name, named_url in urls:
        webhook_url = base_url + reverse(named_url)
        try:
            create_webhook(webhook_name, webhook_url)
        except Exception:
            update_webhook(webhook_name, webhook_url)


def limit_pattern(pattern):
    # Fix up the pattern a bit to avoid it matching some old addresses (which
    # have leaked and are being spammed).

    # Slugs do not start with digits. Fixing this means we no longer match
    # camp-2012-1-officers etc., which helps.
    pattern = pattern.replace("?P<slug>",
                              "?P<slug>[^1-9]")
    return pattern
