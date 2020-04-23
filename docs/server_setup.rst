Server setup
============


Server provisioning/upgrade
---------------------------

To upgrade to a major new version of the OS, it is usually better to start a new
VM, test it is all working, then transfer. Here is the process, assuming that we
are staying with the same provider (DigitalOcean). If moving to a new hosts some
steps will need to be changed.


1. Change the TTL on all cciw.co.uk domains down to 1 hour (3600 seconds), so
   that the downtime caused by a new IP later on will be much quicker. This
   needs to be done at least X seconds before the actual switch over is planned,
   where X is the previous TTL, to give time for DNS propagation. So, if
   previous TTL is 86400 (1 day), this step needs to be done at least 1 day
   before go live of new server.

   Later on, at least 1 hour before switch over, we'll reduce it further to 5
   minutes.

2. Fetch old SSL certificates::

     fab download_letscencrypt_config

3. Create new VM:

   On DigitalOcean, last time (2020-04-18) this process was:

   From https://cloud.digitalocean.com/

   Create new droplet.

   Choose:

   - Latest Ubuntu LTS (last time - 18.04.3 (LTS) x64)
   - Starter plan
   - Smallest box (last time - $5/month, 1 Gb mem, 25 Gb disk, 1000 Gb transfer)
   - London datacenter
   - IPv6 enabled
   - SSH authentication
     - luke@calvin SSH key selected (will need to upload one if there isn't one configured)

   - 1 droplet
   - Hostname: 'cciw' plus an incrementing number (last time: cciw2)

     Use incrementing numbers for each new VM, to ensure you don't confuse with
     previous one. This is not the same as the public domain name. Substitute
     this name wherever ``cciw2`` appears below.

   - Enable backups

4. Add new VM to /etc/hosts so that it can be accessed easily, using the IP address given
   e.g.::

   178.62.115.97 cciw2.digitalocean.com

   Check you can login with ``ssh root@cciw2.digitalocean.com``

5. Change ``env.hosts`` in fabfile to point to new VM. Remember that from now
   on it will use the new VM by default, unless ``-H`` flag is passed.

6. Upgrade versions of things, preferably to defaults for new distribution

   * Python version - see ``PYTHON_BIN`` in fabfile.py
   * Postgresql version - fabfile.py

6. Provision VM::

    $ fab secure
    $ fab provision


  If this fails update any dependencies, searching for new packages using
  ``apt search``.

  Then::

    $ fab upload_letscencrypt_config
    $ fab create_project
    $ fab deploy


The next steps are a 'dry-run', that we will do before the real thing, to check
the process works.


7. Download DB and media from old server. Note use of ``-H`` flag to point to old
   server temporarily::

     fab -H cciw1.digitalocean.com download_usermedia get_live_db

8. Upload media and DB to new server - make sure -H is correct, and change
   ``filename`` to the file downloaded in step 7::

     fab -H cciw2.digitalocean.com upload_usermedia migrate_upload_db:filename

   This may return some errors, while still being successful. Restart webserver::

     fab -H cciw2.digitalocean.com start_webserver

9. Use your local /etc/hosts to point www.cciw.co.uk to the new server, and test
   the new site works as expected.

10. If everything works, prepare to do it for real

    - set the TTL to 5 minutes
    - wait for an hour for DNS to propagate


Now we'll repeat some steps, with changes:

11. Stop the old server

12. Repeat step 7 - download media and DB from old server

13. Repeat step 8 - upload media and DB to new server

14. Repeat step 9 - check everything works

15. Switch DNS to the new server in the DigitalOcean control panel. Put DNS TTL
    back up to 86400

16. Make sure letsencrypt is working::

      fab install_or_renew_ssl_certificate


Done!

Ensure you remove entries from your local /etc/hosts so that you are seeing what
everyone else sees.
