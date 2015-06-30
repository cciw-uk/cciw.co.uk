#!/bin/bash

yum update

# Need epel-release for git
yum install -y epel-release  || exit 1

# Server requirements:
yum install -y postgresql-server.x86_64 postgresql.x86_64 git  || exit 1

# Dev tools for building Python 3.4, and other Python libraries
yum groupinstall -y "Development tools"  || exit 1
yum install -y zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel libxml2-devel libxslt-devel postgresql-devel  || exit 1

# If we do yum update, we need this too, or we get errors with shared folders:
yum install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r) dkms  || exit 1
/etc/init.d/vboxadd setup

# Something for editing files:
yum install -y emacs joe


# To build Python correctly, we need a newer version of gcc
yum install -y gcc44.x86_64 gcc44-c++.x86_64 libstdc++-devel.x86_64  || exit 1


# Custom things to build
cd $HOME
test -d build || mkdir build
cd ~/build

# # Python 3.4:
wget https://www.python.org/ftp/python/3.4.3/Python-3.4.3.tgz || exit 1
tar -xzf Python-3.4.3.tgz || exit 1
cd Python-3.4.3 || exit 1
./configure --with-gcc=/usr/bin/gcc44 --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib" || exit 1
make && make altinstall || exit 1

# Nodejs, needed for lessc
cd ~/build
wget https://nodejs.org/dist/v0.12.5/node-v0.12.5-linux-x64.tar.gz || exit 1
cd /usr/local
sudo tar --strip-components 1 -xzf $HOME/build/node-v0.12.5-linux-x64.tar.gz || exit 1
sudo npm install -g less@1.7.4 || exit 1

# ngrok
cd ~/build
wget https://dl.ngrok.com/ngrok_2.0.19_linux_amd64.zip || exit 1
unzip ngrok_2.0.19_linux_amd64.zip || exit 1
sudo mv ngrok /usr/local/bin/ || exit 1
rm ngrok_2.0.19_linux_amd64.zip

# Setup DB
cd /

# There can sometimes be a setup issue that creates a non-functioning
# /var/lib/pgsql/data dir that stops the rest from working
test -f /var/lib/pgsql/data/pg_ident.conf || rm -rf /var/lib/pgsql/data

service postgresql stop
service postgresql start || exit 1

# Need md5 for password login

cat > /var/lib/pgsql/data/pg_hba.conf <<EOF
# TYPE  DATABASE    USER        CIDR-ADDRESS          METHOD

# "local" is for Unix domain socket connections only
local   all         postgres                          ident sameuser
local   all         all                               md5

# IPv4 local connections:
host    all         all         127.0.0.1/32          md5
# IPv6 local connections:
host    all         all         ::1/128               md5
EOF

chmod ugo+r /var/lib/pgsql/data/pg_hba.conf

service postgresql restart

# Sync passwords with settings_dev.py
sudo -u postgres psql -U postgres -d template1 -c "CREATE DATABASE cciw;"
sudo -u postgres psql -U postgres -d template1 -c "CREATE USER cciw WITH PASSWORD 'foo';"
sudo -u postgres psql -U postgres -d template1 -c "GRANT ALL ON DATABASE cciw TO cciw;" || exit 1
sudo -u postgres psql -U postgres -d template1 -c "ALTER USER cciw CREATEDB;" || exit 1


cat > /home/vagrant/.pgpass <<EOF
*:*:cciw:cciw:foo
EOF

chmod 600 /home/vagrant/.pgpass
chown vagrant.vagrant /home/vagrant/.pgpass

# Make a few things nicer when ssh-ing in.
cat > /home/vagrant/.inputrc <<'EOF'

set match-hidden-files off

set show-all-if-ambiguous on


"\e[A": history-search-backward
"\e[B": history-search-forward

Control-o: menu-complete

"\e[3~": delete-char

EOF

cat > /home/vagrant/.bashrc <<'EOF'
alias ls='ls --color=auto'

shopt -s histappend

. /etc/bashrc

if [ "$TERM" = "screen-256color" ]; then
    export TERM=xterm;
fi

cd /vagrant/src
. ../cciw-venv/bin/activate

EOF
