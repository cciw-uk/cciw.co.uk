Staging servers
===============

We sometimes use a staging server and domain for testing large changes. To create one of these, use the following steps:

1. Create a new droplet on DigitalOcean, the same as the current droplet (or with changes you want to test). See `server_setup.rst <./server_setup.rst>`_. You must give it a name that starts with ``cciw``, and contains ``staging`` e.g. ``cciw-staging``.

2. In DigitlOcean control panel, set ``staging.cciw.co.uk`` to point to the new server. Under the ``cciw.co.uk`` domain, add an ``A`` record with hostname ``staging`` pointing to the new droplet.

3. Provision the new server as per the “Server setup” doc, but:

   - Make sure that instead of ``fab``, you do: ``fab --hosts staging.cciw.co.uk staging``.

     The ``--hosts`` flag means that we connect to the correct server, the ``staging`` command sets some global flags that tweak the config so that ``staging.cciw.co.uk`` will work.

   Roughly, it will look like this. Check::

      fab --hosts staging.cciw.co.uk staging root-hostname

   Then::

      fab --hosts staging.cciw.co.uk staging initial-secure
      fab --hosts staging.cciw.co.uk staging provision
      fab --hosts staging.cciw.co.uk staging upload-letsencrypt-conf
      fab --hosts staging.cciw.co.uk staging create-project
      fab --hosts staging.cciw.co.uk staging deploy --skip-checks
      fab --hosts staging.cciw.co.uk staging install-or-renew-ssl-certificate


   TODO - steps involving SSL are broken:

   - install-or-renew-ssl-certificate needs to come after deploy (otherwise it creates
     directories with bad permissions)
   - but create-project has errors if SSL certificates are not already present.

   - the same issue would happen with production, if we didn’t already have
     certificates from last time. So maybe solve this by downloading staging
     letsencrypt certs.

4. Upload a test database to the new server. This must be a dummy database, not real data.

   TODO - actual steps here

5. When finished, delete the droplet, to avoid bills for it.


Tasks
=====

Deploy
------

Each time you need to deploy new code, you’ll need to do::

  fab --hosts staging.cciw.co.uk staging deploy --skip-checks
