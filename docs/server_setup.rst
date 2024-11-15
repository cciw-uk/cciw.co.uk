Server setup
============


Server provisioning/upgrade
---------------------------

To upgrade to a major new version of the OS, it is usually better to start a new
`VPS <https://en.wikipedia.org/wiki/Virtual_private_server>`_, test it is all
working, then transfer. Here is the process, assuming that we are staying with
the same provider. If moving to a new host, some steps will need to be changed.


1. For all cciw.co.uk domains that point to the DO droplet (usually just the
   ``A`` record), change the TTL on down to 1 hour (3600 seconds), so that the
   downtime caused by a new IP address later on will be much quicker. This needs
   to be done at least X seconds before the actual switch over is planned, where
   X is the previous TTL, to give time for DNS propagation. So, if previous TTL
   is 86400 (1 day), this step needs to be done at least 1 day before going live
   with the new server.

   Later on, at least 1 hour before switch over, we'll reduce it further to 5
   minutes.

   On Digital Ocean, these settings can be done on the `Networking page
   <https://cloud.digitalocean.com/networking/domains>`_.

2. Fetch old SSL certificates::

     fab download-letsencrypt-conf

3. Create new VPS:

   On last time (2020-04-18) this process was:

   From https://cloud.digitalocean.com/

   Create new droplet.

   Choose:

   - London datacenter
   - Latest Ubuntu LTS (last time - 24.04 (LTS) x64)
   - Size: Shared CPU, Basic
   - CPU: Premium Intel, NVMe SSD
   - Smallest box (last time - $8/month, 1 Gb mem, 35 Gb disk, 1000 Gb transfer)

   - SSH authentication
     - choose an SSH key - will need to upload one if there isn't one configured

       This key should be the same as ~/.ssh/id_rsa.pub on the machine you deploy from.

   - Enable backups - weekly
   - Advanced options:
     - Enable IPv6

   - 1 droplet
   - Hostname: 'cciw' plus an incrementing number (last time: cciw4)

     Use incrementing numbers for each new VM, to ensure you don't confuse with
     previous one. This is not the same as the public domain name. Substitute
     this name wherever ``cciw4`` appears below.

   - Project: CCIW

4. Add new VPS to your local /etc/hosts so that it can be accessed easily, using
   the IP address given e.g.::

   167.99.206.14 cciw4.digitalocean.com

   Check you can login to the new VPS with ``ssh root@cciw4.digitalocean.com``

5. Change ``DEFAULT_HOST`` in ``fabfile.py`` to point to the new VPS. Remember that
   from now on it will use the new VPS by default, unless ``-H`` flag is passed.

   Check it has worked by doing ``fab root-hostname``

6. Upgrade versions of dependencies, preferably to defaults for new distribution

   * Python version - see ``PYTHON_BIN`` in fabfile.py
   * Postgresql version - fabfile.py

6. Provision VPS::

    $ fab initial-secure
    $ fab provision


  If this fails to update any dependencies, search for new packages using ``apt
  search``.

  Check you can login to ``root@...``

  Then::

    $ fab upload-letsencrypt-conf
    $ fab create-project

  Check you can login as cciw@...
  Then::

    $ fab deploy --test-host


The next steps are a 'dry-run', that we will do before the real thing, to check
the process works.


7. Download DB and media from old server. Note use of ``-H`` flag to point to old
   server temporarily::

     fab -H cciw2.digitalocean.com download-app-data get-live-db

8. Upload media and DB to new server - make sure -H is correct, and change
   ``<filename>`` to the file downloaded in step 7::

     fab -H cciw4.digitalocean.com upload-app-data stop-all migrate-upload-db <filename>

   This may return some errors, while still being successful. Restart webserver::

     fab -H cciw4.digitalocean.com restart-webserver

9. Use your local /etc/hosts to point www.cciw.co.uk to the new server, and test
   the new site works as expected. Revert /etc/hosts so that you don’t
   confuse yourself.

10. If everything works, prepare to do it for real

    - set the TTL to 5 minutes
    - wait for an hour for DNS to propagate


Now we'll repeat some steps, with changes:

11. Stop the old server (or set to “maintenance mode” somehow, TODO)::

    fab -H cciw2.digitalocean.com stop-all

12. Same as step 7 - download media and DB from old server

13. Same as step 8 - upload media and DB to new server

14. Same as step 9 - check everything works

15. Switch DNS to the new server in the DigitalOcean control panel. Put DNS TTL
    back up to 86400

16. Make sure letsencrypt is working::

      fab install-or-renew-ssl-certificate


Done!

Ensure you remove entries from your local /etc/hosts so that you are seeing what
everyone else sees.

Copy anything else from the old server you might want e.g. goaccess logs?

Stop the old droplet, and eventually destroy it once you are sure everything is
working.

Upgrading
---------

Instead you may opt to upgrade a server in place, with an easier upgrade route
but potentially more downtime if something goes wrong. Use
``do-release-upgrade`` on the server and follow prompts.
