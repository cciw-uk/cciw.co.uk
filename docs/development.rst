CCiW project development
========================

General notes
-------------

The project is a standard `Django <https://www.djangoproject.com/>`_ project,
and should be developed accordingly. The Django documentation, and docs for
other dependencies, will provide reference for most things.

Version control
---------------

Git is used for VCS. Features and fixes should be developed in branches taken
off the 'master' branch. These should be merged to the 'master' branch in order
to deploy.

Servers
-------

In development, you’ll want to run several server processes:

- Django development server::

    ./manage.py runserver

- Django Q scheduled tasks::

    ./manage.py qcluster

- If testing any mail functionality, the ``runmailer_pg`` command. In
  development this will not send real emails, it will just print them to the
  terminal::

    ./manage.py runmailer_pg

It’s recommended to set up a terminal script or session that runs these in
separate tabs at startup (e.g. if using `Kitty
<https://sw.kovidgoyal.net/kitty/>`_ you can use `sessions
<https://sw.kovidgoyal.net/kitty/sessions/>`_).

Tests
-----

Tests can be run with pytest::

  $ pytest

Exclude slow Selenium tests like this::

  $ pytest -m 'not selenium'

See `pytest docs <https://docs.pytest.org/en/latest/>`_ for more info.


Tips
~~~~

* Use ``--show-browser`` with Selenium tests to display the browser.

* put ``fsync = off`` and ``synchronous_commit = off`` in your postgresql.conf
  for large speedups when running tests.


Other
-----

See also:

* `<security.rst>`_.
* `<services.rst>`_.
* `Issues list <https://github.com/cciw-uk/cciw.co.uk/issues>`_ for known bugs or technical debt.
