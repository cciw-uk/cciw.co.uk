import os.path

from fabric.connection import Connection

from . import files


def generate_ssl_dhparams(c: Connection):
    dhparams = "/etc/nginx/ssl/dhparams.pem"
    if not files.exists(c, dhparams):
        d = os.path.dirname(dhparams)
        if not files.exists(c, d):
            c.run(f"mkdir -p {d}")
        c.run(f"openssl dhparam -out {dhparams} 2048", echo=True)
