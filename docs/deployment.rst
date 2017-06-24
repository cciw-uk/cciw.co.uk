Deployment
==========

Deployment is done using the tool Fabric. Once everything is committed to source
control, and "hg status" shows nothing, deploying is as simple as::

  $ fab production deploy

The fabfile contains various other utilities - see ``fab -l``



Crontab
-------

This is not automatically deployed, because the WebFaction account that we
deploy to hosts multiple projects and merging the crontabs for them would get
tricky. Changes to this should be recorded here and then manually installed by
doing 'crontab -e' on the WebFaction server.::

    CCIW_PYTHON=/home/cciw/webapps/cciw_django/venv_py35/bin/python3.5
    CCIW_MANAGE=/home/cciw/webapps/cciw_django/src/manage.py

    CCIW_STAGING_PYTHON=/home/cciw/webapps/cciw_staging_django/venv_py35/bin/python3.5
    CCIW_STAGING_MANAGE=/home/cciw/webapps/cciw_staging_django/src/manage.py

    *       * * * * $CCIW_PYTHON $CCIW_MANAGE send_mail 2>> ~/.django-mailer-cron.log
    5,35    * * * * $CCIW_PYTHON $CCIW_MANAGE fix_mailing_lock
    0,20,40 * * * * $CCIW_PYTHON $CCIW_MANAGE retry_deferred 2>> ~/.django-mailer-deferred-cron.log
    15      1 * * * $CCIW_PYTHON $CCIW_MANAGE clear_securedownload_links
    0       2 * * * $CCIW_PYTHON $CCIW_MANAGE cleanup
    0       7 * * * $CCIW_PYTHON $CCIW_MANAGE payment_reminder_emails

    # expire_bookings must be run only once an hour
    30      * * * * $CCIW_PYTHON $CCIW_MANAGE expire_bookings
    */10    * * * * /home/cciw/webapps/cciw_django/venv_py35/bin/fab -f /home/cciw/webapps/cciw_django/src/fabfile.py production local_webserver_start

    # expire_bookings must be run only once an hour
    30      * * * * $CCIW_STAGING_PYTHON $CCIW_STAGING_MANAGE expire_bookings
    18      1 * * * $CCIW_STAGING_PYTHON $CCIW_STAGING_MANAGE clear_securedownload_links
    3       2 * * * $CCIW_STAGING_PYTHON $CCIW_STAGING_MANAGE cleanup

