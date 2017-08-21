Server setup
============

How the server was set up:

On Digital Ocean, CCIW account, created new VM:

- Ubuntu 16.04.3
- 512 Mb
- Data center: London
- Backups: enabled
- SSH key: ~/.ssh/id_rsa.pub
- hostname: cciw


Then:
- added cciw.digitalocean.com to /etc/hosts

- copied old SSL certificates over to /etc/nginx/ssl::

    $ rsync www.cciw.co.uk.cert root@cciw.digitalocean.com:/etc/nginx/ssl/www.cciw.co.uk.fullchain.pem
    $ rsync www.cciw.co.uk.key root@cciw.digitalocean.com:/etc/nginx/ssl/www.cciw.co.uk.privkey.pem

- Ran::

    $ fab secure
    $ fab provision
    $ fab create_project
    $ fab deploy


- Transferred database from previous host:


- Transferred DNS from previous host:

  - get other host to reduce TTL
  - set up Digital Ocean nameservers for the site. See dns.rst for
    what the record should look like currently.

  - after 24 hours, from domain registrar switch the nameservers
    to point to Digital Ocean

  - optionally, also update the DNS records on the old nameservers to point
    to the new server.

