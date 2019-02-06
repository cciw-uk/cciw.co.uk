CCiW project overview
=====================

Architecture
------------

The CCiW site is fairly standard Django site. It is currently hosted on
DigitalOcean.

We use:

* nginx as main webserver
* postgresql as database
* mailgun for mail services

We currently have no need for async tasks, but do have a crontab for a few
scheduled background tasks.

Other Python dependencies are detailed in ``requirements.txt``.

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
