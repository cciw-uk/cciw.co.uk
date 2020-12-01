Deployment
==========

Deployment is done using the tool Fabric. Once everything is committed to source
control, and "git status" shows nothing, deploying is as simple as::

  $ fab deploy

The fabfile contains various other utilities - see ``fab -l``

If multiple people are working on the project and deploying it, and changes are
made to ``secrets.json`` (which is not in VCS), a secure method for syncing
changes to this file must be agreed on (for example, syncing via the cciw.co.uk
server).
