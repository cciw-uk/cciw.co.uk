import posixpath
from shlex import quote

from fabric.connection import Connection

from . import files


# Users
def user_exists(c: Connection, user_name: str) -> bool:
    return c.run(f"id {quote(user_name)}", hide="both", echo=False, warn=True).ok


def create_user(
    c: Connection,
    user_name: str,
    group: str = None,
    shell: str = "/bin/bash",
    ssh_public_keys: list[str] = None,
):
    """
    Create a new user and its home directory.


    *ssh_public_keys* can be a list of (local) filenames of public keys that should be
    added to the user's SSH authorized keys

    """

    # Note that we use useradd (and not adduser), as it is the most
    # portable command to create users across various distributions:
    # http://refspecs.linuxbase.org/LSB_4.1.0/LSB-Core-generic/LSB-Core-generic/useradd.html

    args = ["--user-group"]
    if shell:
        args.extend(["-s", shell])
    args.append(user_name)
    args_str = " ".join(quote(arg) for arg in args)
    c.run(f"useradd {args_str}", echo=True)
    files.require_directory(c, home_directory(c, user_name), owner=user_name, group=user_name)

    if ssh_public_keys:
        if isinstance(ssh_public_keys, str):
            ssh_public_keys = [ssh_public_keys]
        add_ssh_public_keys(c, user_name, ssh_public_keys)


def add_ssh_public_keys(c: Connection, user_name: str, filenames: list[str]):
    """
    Add multiple public keys to the user's authorized SSH keys.

    *filenames* must be a list of local filenames of public keys that
    should be added to the user's SSH authorized keys.

    Example::

        import fabtools

        fabtools.user.add_ssh_public_keys('alice', [
            '~/.ssh/id1_rsa.pub',
            '~/.ssh/id2_rsa.pub',
        ])

    """
    ssh_dir = posixpath.join(home_directory(c, user_name), ".ssh")
    files.require_directory(c, ssh_dir, mode="700", owner=user_name)

    authorized_keys_filename = posixpath.join(ssh_dir, "authorized_keys")
    files.require_file(c, authorized_keys_filename, mode="600", owner=user_name)

    for filename in filenames:
        with open(filename) as public_key_file:
            public_key = public_key_file.read().strip()

        if public_key not in get_authorized_keys(c, user_name):
            files.append(c, filename=authorized_keys_filename, text=public_key)


def get_authorized_keys(c: Connection, user_name: str) -> list[str]:
    """
    Get the list of authorized SSH public keys for the user
    """

    ssh_dir = posixpath.join(home_directory(c, user_name), ".ssh")
    authorized_keys_filename = posixpath.join(ssh_dir, "authorized_keys")
    data = files.get_file_as_bytes(c, authorized_keys_filename)
    return [line for line in data.decode("utf-8").splitlines() if line and not line.startswith("#")]


def home_directory(c: Connection, name: str):
    """
    Get the absolute path to the user's home directory
    """
    return c.run("echo ~" + name, hide=True).stdout.strip()
