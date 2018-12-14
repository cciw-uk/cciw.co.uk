Development setup
=================

Using local machine
-------------------

(Ideally we would include a Vagrant/Docker setup, but these always seem to be
more trouble than they are worth, they always get out of date if they are not
actually been using for deployment).

Assuming a Linux/Unix machine, the requirements are:

* Python 3.6
* Postgres >= 9.5
* Node

Steps:

These steps have only been tested on Ubuntu-based Linux installations.

* Within a directory of your choice, checkout the CCIW source code into a folder 'src'::

    hg clone ssh://hg@bitbucket.org/cciw/cciw-website src
    cd src

* Make a virtualenv using Python 3.6 e.g. using mkvirtualenv/virtualenv_wrapper::

    mkvirtualenv --python=`which python3.6` cciw

* Create an alias for 'cciw.local' that points to localhost, 127.0.0.1. On
  Linux, you do this by adding the following line to /etc/hosts::

    127.0.0.1          cciw.local

* Install the requirements and a copy of the production DB using the fabfile::

    pip install fabric3 fabtools3
    fab initial_dev_setup


* Run the development server::

    $ ./manage.py runserver 8000

Now you should be able to browse the site on http://cciw.local:8000/
