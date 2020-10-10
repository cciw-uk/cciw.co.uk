Development setup
=================

Using local machine
-------------------

(Ideally we would include a Vagrant/Docker setup, but these always seem to be
more trouble than they are worth, they always get out of date if they are not
actually been using for deployment).

Assuming a Linux/Unix machine, the requirements are:

* Python 3.7
* Postgres 11
* Node

For tests, see also:

* requirements of `django-functest <https://django-functest.readthedocs.io/en/latest/installation.html#dependencies>`_
* requirements of `PyVirtualDisplay <https://github.com/ponty/pyvirtualdisplay#installation/>`_

Steps:

These steps have only been tested on Ubuntu-based Linux installations.

* Within a directory of your choice, checkout the CCiW source code into a folder 'src'::

    hg clone ssh://cciw@cciw.co.uk/repos/cciw-website src
    cd src

* Make a virtualenv using Python 3.7 e.g. using mkvirtualenv/virtualenv_wrapper::

    mkvirtualenv --python=`which python3.7` cciw

* Create an alias for 'cciw.local' that points to localhost, 127.0.0.1. On
  Linux, you do this by adding the following line to /etc/hosts::

    127.0.0.1          cciw.local

* Install the requirements using the fabfile::

    pip install fabric3 fabtools3
    fab initial_dev_setup

* Populate the DB::

    ./manage.py migrate
    ./manage.py loaddata fixtures/dev_db.json

  The dev_fb fixture includes one admin user (username 'admin', password
  'admin') and a snapshot of public data from the production database, but no
  private data.

* Run the development server::

    $ ./manage.py runserver 8000

Now you should be able to browse the site on http://cciw.local:8000/
