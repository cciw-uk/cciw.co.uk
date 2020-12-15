from django.conf import settings
from django.utils import timezone

from .lists import get_all_lists
from .ses import get_active_ruleset_info, RuleSet, save_ruleset, make_ruleset_active, S3Action, Rule

# Some one time AWS/SNS/SES things were set up manually, as described in docs/services.rst
# The remainder is done here.


def setup_ses_routes():
    """
    Setup Amazon SES rule sets
    """
    # We want to enable testing in development, both of:
    # - this function, which sets up rule sets
    # - incoming email handling, which we want to be able
    #   to route to our development machine (via ngrok)
    #   without interfering with production rules.
    #
    # We also don't want to disrupt production rules
    # by temporarily having a broken set of rules.
    #
    # And we do need to clear out old rules (e.g. for old camps) and certain
    # points.
    #
    # Therefore, we have the following strategy:
    #
    # - Create a new ruleset which is a copy of the active one.
    # - Collect and examine all the existing rules within it
    # - Remove all rules relating to our current INCOMING_MAIL_DOMAIN,
    #   and keep everything else.
    # - Add new rules for INCOMING_MAIL_DOMAIN.
    # - Replace old active rule set with the new one we just created.

    active_ruleset = get_active_ruleset_info()
    new_ruleset = RuleSet(name=timezone.now().strftime('Standard %Y-%m-%d %H%M%S'))
    our_domain = settings.INCOMING_MAIL_DOMAIN
    new_ruleset = _copy_other_domain_rules(active_ruleset, new_ruleset, our_domain)
    new_ruleset = _create_new_rules(new_ruleset, our_domain)
    save_ruleset(new_ruleset)
    make_ruleset_active(new_ruleset)


def _copy_other_domain_rules(old_ruleset, new_ruleset, domain):
    for rule in old_ruleset.rules:
        if not all(recipient.endswith('@' + domain)
                   for recipient in rule.recipients):
            new_ruleset.rules.append(rule)

    return new_ruleset


def _create_new_rules(ruleset, domain):
    AWS_INCOMING_MAIL = settings.AWS_INCOMING_MAIL
    recipients = [email_list.address for email_list in get_all_lists()]
    ruleset.rules.append(Rule(
        name=f"Email lists for {domain}",
        recipients=recipients,
        actions=[
            S3Action(
                bucket_name=AWS_INCOMING_MAIL['BUCKET_NAME'],
                topic_arn=AWS_INCOMING_MAIL['TOPIC_ARN']
            )
        ],
        enabled=True,
        scan_enabled=True,
        tls_policy='Optional',
    ))
    return ruleset
