from fabric.connection import Connection


def update_upgrade(c: Connection):
    c.run("DEBIAN_FRONTEND=noninteractive apt update", echo=True)
    c.run("DEBIAN_FRONTEND=noninteractive apt upgrade", echo=True)


def install(c: Connection, packages: list[str]):
    """
    Installs one or more system packages via apt.
    """
    return c.run("DEBIAN_FRONTEND=noninteractive apt-get install -y -q " + " ".join(packages), echo=True)


def remove(c: Connection, packages: list[str]):
    c.run("DEBIAN_FRONTEND=noninteractive apt remove -y " + " ".join(packages), echo=True)
