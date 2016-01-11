#!/bin/sh

cd /vagrant/src

pyvenv-3.4 ../cciw-venv
. ../cciw-venv/bin/activate

pip install --upgrade pip
pip install numpy==1.9.2
pip install -r requirements.txt

test -f $VIRTUAL_ENV/bin/node || nodeenv -p --node=5.4.0
npm install -g --skip-installed less@2.5.3

cat > $VIRTUAL_ENV/lib/python3.4/site-packages/project.pth <<EOF
import sys; sys.__plen = len(sys.path)
/vagrant/src
import sys; new=sys.path[sys.__plen:]; del sys.path[sys.__plen:]; p=getattr(sys,'__egginsert',0); sys.path[p:p]=new; sys.__egginsert = p+len(new)

EOF
