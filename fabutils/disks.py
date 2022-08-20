from fabric.connection import Connection

from . import files


def add_swap(c: Connection, size="1G", swappiness="10"):
    # Needed to compile some things, and for some occassional processes that
    # need a lot of memory.
    if not files.exists(c, "/swapfile"):
        c.run(f"fallocate -l {size} /swapfile", echo=True)
        c.run("chmod 600 /swapfile", echo=True)
        c.run("mkswap /swapfile", echo=True)
        c.run("swapon /swapfile", echo=True)
        files.append(c, "/etc/fstab", "/swapfile   none    swap    sw    0   0\n")

    # Change swappiness so that we actually use the swap
    c.run(f"sysctl vm.swappiness={swappiness}", echo=True)
    files.append(c, "/etc/sysctl.conf", f"vm.swappiness={swappiness}\n")
