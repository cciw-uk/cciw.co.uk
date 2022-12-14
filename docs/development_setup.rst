Development setup
=================

Using local machine
-------------------

(Ideally we would include a Vagrant/Docker setup, but these always seem to be
more trouble than they are worth, they always get out of date if they are not
actually being using for deployment).

Assuming a Linux/Unix machine, the requirements are:

* Python 3.10
* Postgres 14
* bogofilter

For tests, see also:

* requirements of `django-functest <https://django-functest.readthedocs.io/en/latest/installation.html#dependencies>`_

Steps:

These steps have only been tested on Ubuntu-based Linux installations.

* Within a directory of your choice, checkout the CCiW source code into a folder 'src'::

    git clone git@github.com:cciw-uk/cciw.co.uk.git src
    cd src

  Edit your ``.git/config`` and ensure the GitHub remote is called ``origin``
  - this is needed for deploying.

* Make a virtualenv using Python 3.10 e.g. using mkvirtualenv/virtualenv_wrapper::

    mkvirtualenv --python=`which python3.10` -a `pwd` cciw

  Add project path to the venv::

    pwd > $VIRTUAL_ENV/lib/python3.10/site-packages/project.pth

* Create an alias for 'cciw.local' that points to localhost, 127.0.0.1. On
  Linux, you do this by adding the following line to /etc/hosts::

    127.0.0.1          cciw.local

* Install the requirements using the fabfile::

    pip install --upgrade pip wheel
    pip install -r requirements.txt
    fab initial-dev-setup

* Make any local changes needed in ``cciw/settings_local.py``.

* Populate the DB::

    ./manage.py migrate
    ./manage.py loaddata fixtures/dev_db.json

  The dev_db fixture includes one admin user (username 'admin', password
  'admin') and a snapshot of public data from the production database, but no
  private data.

  A larger example DB is available on request.

* Run the development server::

    $ ./manage.py runserver 8000

  Now you should be able to browse the site on http://cciw.local:8000/

* Add pre-commit hooks::

    $ pre-commit install

  (this assumes you have already `installed pre-commit
  <https://pre-commit.com/>`_)

* To be able to mark releases in Sentry, you need Sentry credentials. To
  activate them, you should create a ``cciw_sentry_env`` file like the
  following, preferably stored in an encrypted folder::

    export SENTRY_AUTH_TOKEN=MYSECRETTOKEN

  Then add it to the venv::

    echo "source /path/to/my/cciw_sentry_env" >> $VIRTUAL_ENV/bin/postactivate

See also `<deployment.rst>`_ for docs on deploying, and setup you might
want to do now for that.
