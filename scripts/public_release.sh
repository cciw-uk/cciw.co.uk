#!/bin/bash

# Creates a public release of the CCIW sources
# from the current directories.  Creates both a zip
# file and a tarball.

cd /home/luke/httpd/www.cciw.co.uk/
rm cciw_django_public.tar
tar -cf cciw_django_public.tar --exclude='photos/*.jpeg' --exclude='.svn' --exclude='.bzr' --exclude='django/db/*' --exclude='*~' --exclude='django/tests' --exclude='django/media/images/members/*'  --exclude='django/media/downloads/*' --exclude='django/media/news/*'  --exclude='*.pyc' --exclude='*#' --exclude='django/scripts/*' --exclude='django/scripts' --exclude='django/migrate/*' --exclude 'django/migrate' --exclude='settings_calvin.py' --exclude='settings*_priv.py' --exclude='settings_mysql.py' --exclude='settings_sqlite.py' --exclude='settings_tests.py' --exclude='settings_postgres.py' django/

rm -rf cciw_django_public
mkdir cciw_django_public 
cd cciw_django_public
tar -xf ../cciw_django_public.tar
mv django cciw_django_public
rm ../cciw_django_public.zip
zip -r ../cciw_django_public.zip cciw_django_public
cd ..
rm -rf cciw_django_public


