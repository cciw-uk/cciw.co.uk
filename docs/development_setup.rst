Development setup
=================

Using local machine
-------------------

This assumes a Linux machine, but Windows/Mac may work.

First, install:

- `uv <https://docs.astral.sh/uv/>`_. This will be used to install Python and manage all Python dependencies
- `Nix <https://nix.dev/>`_
- `Devbox <https://www.jetify.com/docs/devbox/>`_. Devbox (which relies on Nix) will install all other “system” dependencies.

- Optionally, install `direnv <https://github.com/direnv/direnv>`_ to make it easier to activate the devbox/uv environments.

For tests, see also:

* requirements of `django-functest <https://django-functest.readthedocs.io/en/latest/installation.html#dependencies>`_

Steps:

These steps have only been tested on Ubuntu-based Linux installations.

* Within a directory of your choice, checkout the CCiW source code into a folder 'src'::

    git clone git@github.com:cciw-uk/cciw.co.uk.git src
    cd src

  Edit your ``.git/config`` and ensure the GitHub remote is called ``origin``
  - this is needed for deploying.

* Switch into the devbox shell. This will take a long time the first time, as everything is installed::

    devbox shell

* Install Python 3.12::

    uv python install 3.12

* Make a virtualenv using Python 3.12::

    uv venv --python python3.12 --prompt cciw

* Install the requirements using uv and then the fabfile::

    uv sync
    uv run fab initial-dev-setup

* Create an alias for 'cciw.local' that points to localhost, 127.0.0.1. On
  Linux, you do this by adding the following line to /etc/hosts::

    127.0.0.1          cciw.local

* Make any local changes needed in ``cciw/settings_local.py``.

* Initialise the Postgres DB files::

    devbox run init_db

* In another terminal, start the services (including Postgres)::

    devbox services up

  You will need to leave this running.

* In the first terminal, create the development database::

    devbox run create_dev_db

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

* To be able to mark releases in Sentry, you need Sentry credentials. To
  activate them, you should create a ``cciw_sentry_env`` file like the
  following, preferably stored in an encrypted folder, and not in the repo::

    export SENTRY_AUTH_TOKEN=MYSECRETTOKEN

  Then add it to the dotenv file ::

    echo "source /path/to/my/cciw_sentry_env" >> .env

See also `<deployment.rst>`_ for docs on deploying, and setup you might
want to do now for that.
