Deployment
==========

To be able to deploy, you need the following:


* Get secrets.json::

    $ fab get_non_vcs_sources

  This requires access to the production server.

* For Sentry release integration after deployment, install ``sentry-cli`` into
  $VIRTUAL_ENV/bin, or elsewhere, as per `installation docs
  <https://docs.sentry.io/product/cli/installation/>`_.

  As described in the `auth docs
  <https://docs.sentry.io/product/cli/configuration/>`_, get a token from
  sentry.io, and put into ~/.sentryclirc, or into an environment variable.

  If you have more than one thing using sentry-cli, environment variables are
  better. They can be put into ``postactivate`` script of the virtualenv.

Deployment is done using the tool Fabric. Once everything is committed to source
control, and "git status" shows nothing, deploying is as simple as::

  $ fab deploy

The fabfile contains various other utilities - see ``fab -l``

If multiple people are working on the project and deploying it, and changes are
made to ``secrets.json`` (which is not in VCS), a secure method for syncing
changes to this file must be agreed on (for example, syncing via the cciw.co.uk
server).
