#!/bin/sh

cd /vagrant/src

pyvenv-3.4 ../cciw-venv
. ../cciw-venv/bin/activate

# OpenSSL issue with old pip version means we need --trusted-host to get this to
# work. Once it is upgraded the problem goes away.
pip install --trusted-host=pypi.python.org --upgrade pip

pip install -r requirements.txt

cat > $VIRTUAL_ENV/lib/python3.4/site-packages/project.pth <<EOF
import sys; sys.__plen = len(sys.path)
/vagrant/src
import sys; new=sys.path[sys.__plen:]; del sys.path[sys.__plen:]; p=getattr(sys,'__egginsert',0); sys.path[p:p]=new; sys.__egginsert = p+len(new)

EOF
