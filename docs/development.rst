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
