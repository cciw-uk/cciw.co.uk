Third party services
====================

Private access details concerning these services are found in the external
"CCiW website access information" document.

PayPal
------

PayPal is integrated using IPN.

To test in development, you will need to use ``fab run_ngrok``.


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

Mailgun
-------

This is used for sending and receiving email. Some email addresses, that don't
need integration with other features, are configured manually using Mailgun's
control panel.

Amazon AWS
----------

This uses a dedicated Amazon AWS account, as described in "CCiW website access
information". IAM roles are described in that document.


S3 Backups
~~~~~~~~~~

An S3 bucket for backups is configured with the following properties:

* Region: EU West 2 (London)
* Created bucket with following settings

  * name: (see secrets.json)
  * Block all public access: enabled
  * Bucket versioning: disabled
  * Server side encryption: enabled

    * Amazon S3 key
  * Lifecycle rule:

    * Name: "Delete after 30 days"
    * Scope: "This rule applies to all objects in the bucket"
    * Action: "Expire current versions of objects"

      * Number of days after object creation: 30

    * Action: "Delete expired delete markers or incomplete multipart uploads"

      * Delete incomplete multipart uploads: checked
      * Numbers of days: 30

Note that the lifecycle policy is an important part of our data retention and
data privacy policy - old data that we want to delete will be expunged from our
backups as well as our main database once the backup is automatically deleted.

SES Simple Email Service
~~~~~~~~~~~~~~~~~~~~~~~~

SES was set up as follows:

Using the main account, added 'cciw.co.uk' as a verified domain.

* Verify a new domain ->

  * Domain: cciw.co.uk
  * Generate DKIM Settings: enabled

* Added domain verification records in DNS (DigitalOcean) as per instructions.

* Under "SMTP settings"

  * In secrets.json, "SMTP_HOST" and "SMTP_PORT" set from data given

  * Created new user for SES sending.

    * Made note of auth settings - copied to password store and to secrets.json as
      "SMTP_USERNAME" and "SMTP_PASSWORD".

    * Also make note of MX record needed (inbound SMTP server)

* Under 'Email addresses', added web master personal email address to test
  sending.

* Under 'Domains', selected 'cciw.co.uk' and sent test email.

* Under 'Sending statistics', chose 'Edit your account details' to ask Amazon to
  enable production usage.

This was done for both eu-west-2 (London) and eu-west-1 (Ireland), because
eu-west-2 doesn't have support for inbound email (yet).


Receiving
~~~~~~~~~

Based on this guide:

https://aws.amazon.com/blogs/messaging-and-targeting/forward-incoming-email-to-an-external-destination/

* In Amazon S3, a bucket was created to store incoming mail temporarily with following settings

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
  from the secrets.json

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

  This role can be used for Lambda functions, and also for
  our own mail handing.


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

  * Name: webmaster-forward

  * Enabled
  * Enable spam and virus checking: enabled

  * Added necessary permissions


* In Amazon SNS, for topic ses-incoming-notification:

  * Created subscription:

    * Protocol: HTTPS
    * Endpoint: https://www.cciw.co.uk/mail/ses-incoming-notification/
    * Enable raw message delivery: disabled
    * Use the default delivery retry policy: enabled

  * Chose 'Request confirmation' to send confirmation request to endpoint. This
    was initially done for development (see below), later for live endpoint.


When setting this up and debugging:

* instead of adding an MX record for ``cciw.co.uk``, you can add one for
  ``mailtest.cciw.co.uk`` and use addresses like
  ``webmaster@mailtest.cciw.co.uk``.

* for testing the subscription and the handler, use ngrok, and set up a
  subscription that posts to the ngrok address instead of the live one (which
  might not be deployed yet)

* if you want to test real email sending from a development machine, be sure to
  change cciw/settings.py so that you are using the real SMTP server
  EMAIL_BACKEND and not the dummy 'console'.
