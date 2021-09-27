from django.conf import settings
from django.utils import timezone

from .lists import get_all_lists
from .ses import (
    Rule,
    RuleSet,
    S3Action,
    delete_ruleset,
    get_active_ruleset_info,
    get_all_rulesets,
    make_ruleset_active,
    save_ruleset,
)

# Some one time AWS/SNS/SES things were set up manually, as described in docs/services.rst
# The remainder is done here.


def setup_ses_routes():
    """
    Setup Amazon SES rule sets
    """
    # We want to enable testing in development, both of:
    #
    # - this function, which sets up rule sets.
    #
    # - incoming email handling, which we want to be able to route to our
    #   development machine (via ngrok) without interfering with production
    #   rules. This uses a different domain to the production domain, with
    #   prefix 'mailtest.'
    #
    # However in Amazon SES we can only have one 'ruleset' active, and it needs
    # to have both production and development rules in it. We don't want to
    # disrupt production, even temporarily, by having a broken set of rules. For
    # this reason, in development we have to be careful to keep the 'other
    # domain' working (the 'other' domain is production if we are running this
    # function in development environment, and vice versa)
    #
    # The following process is designed with these things in mind.

    active_ruleset = get_active_ruleset_info()
    new_ruleset = RuleSet(name=timezone.now().strftime("Standard %Y-%m-%d %H%M%S"))
    our_domain = settings.INCOMING_MAIL_DOMAIN
    new_ruleset = _copy_other_domain_rules(active_ruleset, new_ruleset, our_domain)
    new_ruleset = _create_new_rules(new_ruleset, our_domain)
    save_ruleset(new_ruleset)
    make_ruleset_active(new_ruleset)
    _cleanup_old_rulesets(new_ruleset)


def _copy_other_domain_rules(old_ruleset, new_ruleset, domain):
    for rule in old_ruleset.rules:
        if not all(recipient.endswith("@" + domain) for recipient in rule.recipients):
            new_ruleset.rules.append(rule)

    return new_ruleset


def _create_new_rules(ruleset, domain):
    AWS_INCOMING_MAIL = settings.AWS_INCOMING_MAIL
    recipients = [email_list.address for email_list in get_all_lists()]
    ruleset.rules.append(
        Rule(
            name=f"Email lists for {domain}",
            recipients=recipients,
            actions=[S3Action(bucket_name=AWS_INCOMING_MAIL["BUCKET_NAME"], topic_arn=AWS_INCOMING_MAIL["TOPIC_ARN"])],
            enabled=True,
            scan_enabled=True,
            tls_policy="Optional",
        )
    )
    return ruleset


def _cleanup_old_rulesets(active_ruleset):
    all_rulesets = get_all_rulesets()
    old_rulesets = [ruleset for ruleset in all_rulesets if ruleset.name != active_ruleset]
    old_rulesets.sort(key=lambda r: r.created_timestamp, reverse=True)
    for ruleset in old_rulesets[10:]:
        # We leave a few old ones behind for debugging,
        # and so we can easily restore something if needed.
        delete_ruleset(ruleset)
