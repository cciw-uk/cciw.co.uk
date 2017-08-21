Deployment
==========

Deployment is done using the tool Fabric. Once everything is committed to source
control, and "hg status" shows nothing, deploying is as simple as::

  $ fab production deploy

The fabfile contains various other utilities - see ``fab -l``
