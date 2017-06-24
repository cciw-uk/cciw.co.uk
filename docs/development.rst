CCIW project development
========================

General notes
-------------

The project is a standard `Django <https://www.djangoproject.com/>`_ project,
and should be developed accordingly. The Django documentation, and docs for
other dependencies, will provide reference for most things.

Views are done using a mixture of classic functions and Class Based Views,
depending on whether the move to CBVs was worth the effort. This means that
there is sometimes some duplication between the function based way of doing
something and the equivalent CBV way, and you need to be comfortable with both
styles.

Note that we use our own, simplified CBV base class. See
https://lukeplant.me.uk/blog/posts/my-approach-to-class-based-views/ for more
explanation of the rationale here.


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

Other
-----

See also:

* `<security.rst>`_.
* `<services.rst>`_.
