Third party services
====================

Private access details concerning these services are found in the external
password store.

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

This uses a dedicated Amazon AWS account.


S3 Backups
~~~~~~~~~~

An S3 bucket for backups is configured with the following properties:

* Located S3 service
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

Note that the lifecycle policy is an important part of our data retention and
data privacy policy - old data that we want to delete will be expunged from our
backups as well as our main database once the backup is automatically deleted.
