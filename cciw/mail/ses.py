# Utilities for dealing with our Amazon Simple Email Service integration
import io
import re
import warnings
from datetime import datetime
from typing import List

import attr
import boto3
from django.conf import settings


# General
def get_config_boto_session():
    CONFIG_USER = settings.AWS_CONFIG_USER
    session = boto3.Session(aws_access_key_id=CONFIG_USER['ACCESS_KEY_ID'],
                            aws_secret_access_key=CONFIG_USER['SECRET_ACCESS_KEY'],
                            region_name=CONFIG_USER['REGION_NAME'])
    return session


# S3
def download_ses_message_from_s3(message_id):
    AWS_INCOMING_MAIL = settings.AWS_INCOMING_MAIL
    session = boto3.Session(aws_access_key_id=AWS_INCOMING_MAIL['ACCESS_KEY_ID'],
                            aws_secret_access_key=AWS_INCOMING_MAIL['SECRET_ACCESS_KEY'],
                            region_name=AWS_INCOMING_MAIL['REGION_NAME'])

    s3 = session.resource('s3')
    bucket = s3.Bucket(name=AWS_INCOMING_MAIL['BUCKET_NAME'])
    store = io.BytesIO()
    bucket.download_fileobj(message_id, store)
    return store.getvalue()


# SES
# https://docs.aws.amazon.com/ses/latest/DeveloperGuide/receiving-email-receipt-rule-set.html


def get_ses_api():
    return get_config_boto_session().client('ses')


class Action:
    @classmethod
    def from_api(cls, data):
        if 'S3Action' in data:
            return S3Action.from_api(data['S3Action'])

        warnings.warn(f'Unrecognised action {data}')
        return None


@attr.s(auto_attribs=True)
class S3Action(Action):
    bucket_name: str
    topic_arn: str

    @classmethod
    def from_api(cls, data):
        return cls(
            bucket_name=data['BucketName'],
            topic_arn=data['TopicArn']
        )

    def to_api(self):
        # https://docs.aws.amazon.com/ses/latest/APIReference/API_ReceiptAction.html
        # https://docs.aws.amazon.com/ses/latest/APIReference/API_S3Action.html
        return {
            'S3Action': {
                'BucketName': self.bucket_name,
                'TopicArn': self.topic_arn,
            }
        }


@attr.s(auto_attribs=True)
class Rule:
    name: str
    recipients: List[str]
    actions: List[Action]
    enabled: bool
    scan_enabled: bool
    tls_policy: str = 'Optional'

    def __attrs_post_init__(self):
        self.name = _clean_name(self.name)

    @classmethod
    def from_api(cls, data):
        return cls(
            name=data['Name'],
            recipients=data['Recipients'],
            actions=[
                Action.from_api(item)
                for item in data['Actions']
            ],
            enabled=data['Enabled'],
            scan_enabled=data['ScanEnabled'],
            tls_policy=data['TlsPolicy'],
        )

    def to_api(self):
        # https://docs.aws.amazon.com/ses/latest/APIReference/API_ReceiptRule.html
        return {
            'Name': self.name,
            'Recipients': self.recipients,
            'Actions': [
                action.to_api() for action in self.actions
            ],
            'Enabled': self.enabled,
            'ScanEnabled': self.scan_enabled,
            'TlsPolicy': self.tls_policy,
        }


class Missing:
    """
    Sentinel object used to indicate attributes of an object that were not
    populated (e.g. when created from an API that didn't supply all details)
    """
    # This is to help avoid data loss bugs if a partially populated
    # object mistakenly gets passed back to the wrong API - hopefully
    # we'll get an error when we try to serialize.
    def __bool__(self):
        self._raise()

    def __eq__(self, other):
        self._raise()

    def _raise(self):
        raise ValueError('The only valid thing to do with me is `is Missing`')

    def __repr__(self):
        return 'Missing'


Missing = Missing()


@attr.s(auto_attribs=True)
class RuleSet:
    name: str
    created_timestamp: datetime = Missing
    rules: List[Rule] = attr.Factory(list)

    def __attrs_post_init__(self):
        self.name = _clean_name(self.name)

    @classmethod
    def from_api(cls, data):
        return cls(
            name=data['Metadata']['Name'],
            created_timestamp=data['Metadata']['CreatedTimestamp'],
            rules=[
                Rule.from_api(item)
                for item in data['Rules']
            ] if 'Rules' in data else Missing,
        )

    @classmethod
    def from_list_api(cls, data):
        rulesets = data['RuleSets']
        return [cls(name=ruleset['Name'],
                    created_timestamp=ruleset['CreatedTimestamp'],
                    rules=Missing)
                for ruleset in rulesets]


def get_active_ruleset_info():
    ses_api = get_ses_api()
    return RuleSet.from_api(ses_api.describe_active_receipt_rule_set())


def get_all_rulesets():
    ses_api = get_ses_api()
    return RuleSet.from_list_api(ses_api.list_receipt_rule_sets())


def save_ruleset(ruleset: RuleSet):
    ses_api = get_ses_api()
    # https://docs.aws.amazon.com/ses/latest/APIReference/API_CreateReceiptRuleSet.html
    rule_set_response = ses_api.create_receipt_rule_set(RuleSetName=ruleset.name)
    _assert_200(rule_set_response)

    for i, rule in enumerate(ruleset.rules):
        if i > 0:
            previous_rule = ruleset.rules[i - 1]
        else:
            previous_rule = None
        # https://docs.aws.amazon.com/ses/latest/APIReference/API_CreateReceiptRule.html
        args = dict(
            Rule=rule.to_api(),
            RuleSetName=ruleset.name,
        )
        if previous_rule is not None:
            args.update(dict(After=previous_rule.name))

        rule_response = ses_api.create_receipt_rule(**args)
        _assert_200(rule_response)


def make_ruleset_active(ruleset: RuleSet):
    ses_api = get_ses_api()
    ses_api.set_active_receipt_rule_set(RuleSetName=ruleset.name)


def delete_ruleset(ruleset: RuleSet):
    ses_api = get_ses_api()
    ses_api.delete_receipt_rule_set(RuleSetName=ruleset.name)


def _assert_200(api_data):
    assert api_data['ResponseMetadata']['HTTPStatusCode'] == 200


def _clean_name(name):
    return re.subn('[^a-zA-Z0-9_-]', '_', name)[0]
