CCIW source code
================

The CCIW site is fairly standard Django site. It is currently hosted on
WebFaction shared hosting and makes use of some of its API and email features.

Development setup
-----------------

The easiest way is to use Vagrant and the provided Vagrantfile which will set up
a development VM that is fairly close to the WebFaction shared server we are
using. On the host machine, install:

    Vagrant  https://www.vagrantup.com/
    A Vagrant backend e.g. VirtualBox
    Mercurial https://mercurial.selenic.com/

The following method should work on any host machine (Linux, Windows, Mac) which
supports the above dependencies. Once you have installed them:

* On the host machine, create an alias for 'cciw.local' that points to
  localhost, 127.0.0.1. On Linux, you do this by adding the following line to
  /etc/hosts::

    127.0.0.1          cciw.local

* On the host machine, create a folder "cciw.co.uk" to hold source code and
  related files.

* Within it, checkout the CCIW source code into a folder 'src'::

    hg clone ssh://hg@bitbucket.org/spookylukey/cciw-website src

  These folders will be shared between the host and the VM, so you can
  edit the source code from your host machine if wanted.

* In the src directory, do::

    $ vagrant plugin install vagrant-vbguest
    $ vagrant up

  (Go bake a cake while it runs...)

* Once completed, do::

    $ vagrant ssh

    # Now you are in the VM, with the right current directory
    # and the virtualenv already activated.

    # Some initial dev setup tasks:
    $ fab initial_dev_setup

    # Run the development server:
    $ ./manage.py runserver 0.0.0.0:8000

  You should now have a development copy of the site running, on port 8000 in
  the VM. Vagrant has mapped this to port 9000 on the host, so you
  can access http://cciw.local:9000/ on the host, and should see the CCIW site.


Alternatively, you can use a virtualenv on the host machine, and look in the
Vagrantfile and associated scripts for information about the things you will
need installed.

Version control
---------------

Mercurial is used for VCS. Features and fixes should be developed off the
'default' named branch, using bookmarks if necessary. These are merged to the
'live' named branch as part of the deployment process.

Tests
-----

Tests can be run like so::

  $ ./runtests.py

or::

  $ ./runtests.py cciw.bookings.tests.SomeSpecificTest

Deployment
----------

Deployment is done using the tool Fabric. Once everything is committed to source
control, and "hg status" shows nothing, deploying is as simple as::

  $ fab production deploy

The fabfile contains various other utilities - see ``fab -l``


Components
----------

The major components of the site are:

1) Information about the camps that are run. This is all on publically
   accessible parts of the site.

2) Booking - for campers (or their parents) to book places on camp and pay.

3) Admin.

   Used by a few people to add camp information, for example. Also used by
   booking secretary to add/manage information about bookings, and various other
   staff functions.

4) Leaders and officers.

   This contains utilities for leaders:

   * to manage an officer list for their camp
   * to view applications from officers
   * to manage references for officers
   * to download booking information about campers booked on the camp

   …and other things

   It also contains utilities for officers to submit their application forms,
   and helps for the booking secretary.

   Where possible, the Django admin is used for some of these functions.

There used to be a 'forums' section with photos, topics, members etc. and its
own login system. This is almost entirely unused since 2007 and removed in 2015.
Backups of the data are available.

Login
-----

Because of the above components, there are 2 separate login systems:

* The standard django.contrib.auth system, with a custom AUTH_USER_MODEL,
  used by the Django admin and the officers section (staff members).

* A custom login system for booking places on camp, which is passwordless, based
  on BookingAccount.

Layout
------

The project uses an old style layout, with all the apps inside the 'cciw'
module.

Some of the apps do not have their own views, because of the connections between
different models. So a lot of view functions are in cciw.cciwmain.views.

The 'officers' and 'bookings' apps are structured in a more obvious way and are
more separated than the other apps, although there are still strong dependencies
between apps.


Other notes
-----------

Views are done using a mixture of classic functions and Class Based Views,
depending on whether the move to CBVs was worth the effort. This means that
there is sometimes some duplication between the function based way of doing
something and the equivalent CBV way, and you need to be comfortable with both
styles. Note that we use our own, simplified CBV base class.


Crontab
-------

This is not automatically deployed, because the WebFaction account that we
deploy to hosts multiple projects and merging the crontabs for them would get
tricky. Changes to this should be recorded here and then manually installed by
doing 'crontab -e' on the WebFaction server.::

    CCIW_PYTHON=/home/cciw/webapps/cciw_django/venv_py34/bin/python3.4
    CCIW_MANAGE=/home/cciw/webapps/cciw_django/src/manage.py

    CCIW_STAGING_PYTHON=/home/cciw/webapps/cciw_staging_django/venv_py34/bin/python3.4
    CCIW_STAGING_MANAGE=/home/cciw/webapps/cciw_staging_django/src/manage.py

    *       * * * * $CCIW_PYTHON $CCIW_MANAGE send_mail 2>> ~/.django-mailer-cron.log
    5,35    * * * * $CCIW_PYTHON $CCIW_MANAGE fix_mailing_lock
    0,20,40 * * * * $CCIW_PYTHON $CCIW_MANAGE retry_deferred 2>> ~/.django-mailer-deferred-cron.log
    15      1 * * * $CCIW_PYTHON $CCIW_MANAGE clear_securedownload_links
    */10    * * * * $CCIW_PYTHON $CCIW_MANAGE process_payments
    0       2 * * * $CCIW_PYTHON $CCIW_MANAGE cleanup
    *       * * * * $CCIW_PYTHON $CCIW_MANAGE handle_mailing_lists 2>> ~/.cciw-mailings-cron.log
    0       7 * * * $CCIW_PYTHON $CCIW_MANAGE payment_reminder_emails

    # expire_bookings must be run only once an hour
    30      * * * * $CCIW_PYTHON $CCIW_MANAGE expire_bookings
    */10    * * * * /home/cciw/webapps/cciw_django/venv_py34/bin/fab -f /home/cciw/webapps/cciw_django/src/fabfile.py production local_webserver_start

    # expire_bookings must be run only once an hour
    30      * * * * $CCIW_STAGING_PYTHON $CCIW_STAGING_MANAGE expire_bookings
    18      1 * * * $CCIW_STAGING_PYTHON $CCIW_STAGING_MANAGE clear_securedownload_links
    3       2 * * * $CCIW_STAGING_PYTHON $CCIW_STAGING_MANAGE cleanup


PayPal
======

PayPal is integrated using IPN.

To test in development, you will need to use ``fab run_ngrok``.


Accounts
--------

The most confusing thing about PayPal is all the accounts.

The main account for receiving money: paypal@cciw.co.uk

In addition, there are sandbox accounts for testing.

Sandbox
~~~~~~~

This is managed from:

Site: https://developer.paypal.com
Login: paypal@cciw.co.uk

From this site, you can create/manage various sandbox accounts which play the
role of buyer/seller:

https://developer.paypal.com/developer/accounts

'Buyer' account:
Email: paypal-buyer@cciw.co.uk
Password: asdfghjk

'Seller' account - this is the one you need to test PayPal interactions in development
Email: paypal-facilitator@cciw.co.uk
Password: qwertyui

These accounts can be used to log in on www.sandbox.paypal.com/
