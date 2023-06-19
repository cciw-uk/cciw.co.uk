Third party services
====================

Private access details concerning these services are found in the external
"CCiW website access information" document.

PayPal
------

PayPal is integrated using IPN.

If making major changes to the PayPal integration and need to fully test the
flow in development, you will need to use something like `ngrok
<https://ngrok.com/docs/secure-tunnels/tunnels/>`_ to create a public (temporary) domain name that forwards
to your local development machine, so that the (sandbox) PayPal server can post
back to your development machine.

.. code-block:: shell

   ngrok http 8000

(assuming you are running the development server on port 8000, and have already
installed and configured ngrok locally)

Accounts
~~~~~~~~

The most confusing thing about PayPal is all the accounts.

The main account for receiving money: paypal@cciw.co.uk

In addition, there are sandbox accounts for testing.

Sandbox
~~~~~~~

This is managed from:

* Site: https://developer.paypal.com
* Login: paypal@cciw.co.uk
* Password - see password store

From this site, you can create/manage various sandbox accounts which play the
role of buyer/seller:

https://developer.paypal.com/developer/accounts

'Buyer' account:

* Email: paypal-buyer@cciw.co.uk
* Password: asdfghjk

'Seller' account - this is the one you need to test PayPal interactions in development

* Email: paypal-facilitator@cciw.co.uk
* Password: qwertyui

These accounts can be used to log in on https://www.sandbox.paypal.com/

NB. The inclusion of these passwords in this public repo is not a security
consideration, since they are only sandbox passwords.

Amazon AWS
----------

All AWS services are part of a dedicated Amazon AWS account, as described in
"CCiW website access information". IAM roles are described in that document.
Individual services are described below.

Amazon S3 Backups
-----------------

An S3 bucket for backups is configured with the following properties:

* Region: EU West 2 (London)
* Created bucket with following settings

  * name: (see secrets.json)
  * Block all public access: enabled
  * Bucket versioning: disabled
  * Server side encryption: enabled

    * Amazon S3 key

  * Lifecycle rule:

    * Name: "Delete after 60 days"
    * Scope: "This rule applies to all objects in the bucket"
    * Action: "Expire current versions of objects"

      * Number of days after object creation: 60

    * Action: "Delete expired delete markers or incomplete multipart uploads"

      * Delete incomplete multipart uploads: checked
      * Numbers of days: 60

Note that the lifecycle policy is an important part of our data retention and
data privacy policy - old data that we want to delete will be expunged from our
backups as well as our main database once the backup is automatically deleted.

SES Simple Email Service
------------------------

SES is used for sending and receiving email. The overall architecture is:

Sending:

* The Django app sends mail via a normal SMTP connection to Amazon SES.
* We get bounce notifications (used in some cases to notify leaders of incorrect
  email addresses), as follows:

  * Bounces are sent to a Amazon SNS topic by SES.
  * There is a subscription to that topic for an endpoint on the web app,
    which handles the bounce.

Receiving:

* In DNS, we have an MX record pointing mail to Amazon SES servers. Settings
  provided by Amazon - see
  https://docs.aws.amazon.com/ses/latest/DeveloperGuide/receiving-email-mx-record.html

* In SES, we have a "rule set" that matches various email addresses and
  directs the emails to an action that:

  * Stores the emails in S3
  * Sends a notification via an SNS topic.

* We have a subscription to that SNS topic that posts to an endpoint on our web
  app. This endpoint (part of the app) finally handles the mail.

  * Which normally involves sending out other emails, but could be anything.


Sending setup
~~~~~~~~~~~~~

SES was set up as follows:

Using the main account, added 'cciw.co.uk' as a verified domain.

* Verify a new domain ->

  * Domain: cciw.co.uk
  * Generate DKIM Settings: enabled

* Added domain verification records in DNS as per instructions.

* Under "SMTP settings"

  * In secrets.json, "SMTP_HOST" and "SMTP_PORT" set from data given

  * Created new user for SES sending.

    * Made note of auth settings - copied to password store and to secrets.json as
      "SMTP_USERNAME" and "SMTP_PASSWORD".

    * Also made note of MX record needed (inbound SMTP server)

* Under 'Email addresses', added web master personal email address to test
  sending.

* Under 'Domains', selected 'cciw.co.uk' and sent test email.

* Under 'Sending statistics', chose 'Edit your account details' to ask Amazon to
  enable production usage.

This was done for both eu-west-2 (London) and eu-west-1 (Ireland). Because
eu-west-2 doesn't have support for inbound email (yet), we use eu-west-1 only
(both send and receive).

Bounce notification
~~~~~~~~~~~~~~~~~~~

Some guides that have helpful info:

* https://aws.amazon.com/premiumsupport/knowledge-center/ses-bounce-notifications-sns/

Actions:

* In Amazon SNS, created topic:

  * Region: eu-west-1 (Ireland)
  * Type: Standard
  * Name: ses-bounces
  * Display name: SES bounces

* Added subscription to the topic:

  * Protocol: HTTPS
  * Endpoint: https://www.cciw.co.uk/mail/ses-bounce/
  * Enable raw message delivery: disabled
  * Use the default delivery retry policy: enabled
  * Confirmed subscription using 'Request confirmation'

* In Amazon SES, under 'Domains' -> cciw.co.uk -> Notifications -> Edit configuration:

  * SNS Topic Configuration:

    * Bounces:

      * Topic: ses-bounces
      * Include original headers: enabled

  * Email feedback forwarding: enabled

* Testing: https://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-email-simulator.html


Receiving
~~~~~~~~~

With information from the following guides (but adapted):

* https://aws.amazon.com/blogs/messaging-and-targeting/forward-incoming-email-to-an-external-destination/

* https://docs.aws.amazon.com/sns/latest/dg/sns-subscribe-https-s-endpoints-to-topic.html

Actions:

* In Amazon S3, a bucket was created to store incoming mail temporarily with following settings:

  * Region: EU West 1 (Ireland)
  * Name: (see secrets.json)
  * Block all public access: enabled
  * Bucket versioning: disabled
  * Server side encryption: enabled

    * Amazon S3 key

  * Lifecycle rule:

    * Name: "Delete after 5 days"
    * Scope: "This rule applies to all objects in the bucket"
    * Action: "Expire current versions of objects"

      * Number of days after object creation: 5

    * Action: "Delete expired delete markers or incomplete multipart uploads"

      * Delete incomplete multipart uploads: checked
      * Numbers of days: 5

* Added the following bucket policy to the bucket::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowSESPuts",
                "Effect": "Allow",
                "Principal": {
                    "Service": "ses.amazonaws.com"
                },
                "Action": "s3:PutObject",
                "Resource": "arn:aws:s3:::<BUCKET_NAME>/*",
                "Condition": {
                    "StringEquals": {
                        "aws:Referer": "<USER_ID>"
                    }
                }
            }
        ]
    }

  with ``<BUCKET_NAME>`` and ``<USER_ID>`` replaced by values
  from secrets.json

* Added IAM policy with following contents::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "VisualEditor0",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents"
                ],
                "Resource": "*"
            },
            {
                "Sid": "VisualEditor1",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "ses:SendRawEmail"
                ],
                "Resource": [
                    "arn:aws:s3:::<BUCKET_NAME>/*",
                    "arn:aws:ses:<REGION_NAME>:<USER_ID>:identity/*"
                ]
            }
        ]
    }

  with ``<BUCKET_NAME>``, ``<REGION_NAME>`` and ``<USER_ID>`` replaced by values
  from the secrets.json

  Named: incoming-mail-handler

  This role can be used for Lambda functions, and also for our own mail handing.


* Created ruleset:

  * Recipients:

    * webmaster@cciw.co.uk
    * webmaster@mailtest.cciw.co.uk

  * Actions:

    * S3

      * Bucket: <BUCKET_NAME>
      * Key prefix: <empty>
      * SNS topic:

        * Create New Topic:

          * Topic Name: ses-incoming-notification
          * Display Name: SES incoming notification
          * Copied notification ARN to secrets.json

  * Name: webmaster-forward

  * Enabled
  * Enable spam and virus checking: enabled

  * Added necessary permissions


* This ruleset and all rules were later recreated via a script, but it is easiest
  to setup notifications using the console.

* In Amazon SNS, for topic ses-incoming-notification:

  * Created subscription:

    * Protocol: HTTPS
    * Endpoint: https://www.cciw.co.uk/mail/ses-incoming-notification/
    * Enable raw message delivery: disabled
    * Use the default delivery retry policy: enabled

  * Chose 'Request confirmation' to send confirmation request to endpoint. This
    was initially done for development (see below), later for live endpoint.


Development
~~~~~~~~~~~

The above actions and configuration represent the final, production config. When
setting this up, it can help to do so from a development machine using test
values, especially if there is an existing setup that you are trying not to
disturb.

Here is how to do that:

* For sending SES email, you don't need to worry - you can send from
  ``@cciw.co.uk`` addresses from multiple different SMTP servers at the same
  time. When adding DNS records necessary for confirmation, simply add the new
  ones while leaving the old ones in place - they don't clash.

* For receiving, instead of adding an MX record for ``cciw.co.uk``, you can add
  one for ``mailtest.cciw.co.uk``, leaving the active cciw.co.uk record as it is
  until the end.

* When creating rule sets for receiving email and matching emails, use addresses
  like ``webmaster@mailtest.cciw.co.uk``.

* For testing the SNS subscription and the web app handler, use ngrok, and set
  up an HTTPS subscription to the SNS topic that posts to the ngrok address of
  your development server instead of the live one (which might not be deployed
  yet).

* If you want to test real email sending from a development machine, be sure to
  change ``cciw/settings.py`` so that you are using the real SMTP server
  ``EMAIL_BACKEND`` and not the dummy 'console' one.

* 'HTTPS endpoint' subscriptions to SNS topics have to be confirmed before they
  can be used. The ``@confirm_sns_subscriptions`` decorator does this
  automatically, assuming the endpoint is available (e.g. via ngrok if
  developing, or live on the production site). You may need to manually choose
  'Request confirmation' in the AWS console to trigger this.
