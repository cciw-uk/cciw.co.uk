Development setup
=================

The easiest way is to use Vagrant and the provided Vagrantfile which will set up
a development VM that is fairly close to the WebFaction shared server we are
using. On the host machine, install:

* `Vagrant <https://www.vagrantup.com/>`_
* A Vagrant backend e.g. `VirtualBox <https://www.virtualbox.org/>`_
* `Mercurial <https://mercurial.selenic.com/>`_

The following method should work on any host machine (Linux, Windows, Mac) which
supports the above dependencies. Once you have installed them:

* On the host machine, create an alias for 'cciw.local' that points to
  localhost, 127.0.0.1. On Linux, you do this by adding the following line to
  /etc/hosts::

    127.0.0.1          cciw.local

* On the host machine, create a folder "cciw.co.uk" to hold source code and
  related files.

* Within it, checkout the CCIW source code into a folder 'src'::

    hg clone ssh://hg@bitbucket.org/cciw/cciw-website src

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
