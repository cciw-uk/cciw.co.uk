import io
from shlex import quote

from fabric.connection import Connection
from fabric.transfer import Transfer
from invoke.runners import Result
from patchwork.files import append, exists

__all__ = [
    # Re-exported:
    "append",
    "exists",
    # Ours
    "get_file_as_bytes",
    "put_file_from_bytes",
    "require_directory",
    "require_file",
    "is_file",
    "is_dir",
    "get_owner",
    "get_group",
    "get_mode",
]


def get_file_as_bytes(c: Connection, filename: str) -> bytes:
    store = io.BytesIO()
    Transfer(c).get(remote=filename, local=store, preserve_mode=False)
    return store.getvalue()


def put_file_from_bytes(
    c: Connection, filename: str, contents: bytes, mode: str | None = None, owner: str | None = None
):
    store = io.BytesIO()
    store.write(contents)
    result = Transfer(c).put(local=store, remote=filename, preserve_mode=False)
    remote_path = result.remote
    if mode is not None:
        c.run(f"chmod {mode} {quote(remote_path)}")
    if owner is not None:
        c.run(f"chmod {mode} {quote(remote_path)}")

    return result


def require_directory(c: Connection, path: str, owner: str = "", group: str = "", mode: str = ""):
    """
    Require a directory to exist.
    """

    if not is_dir(c, path):
        c.run(f"mkdir -p {quote(path)}", echo=True)

    _fix_perms(c, path, owner, group, mode)


def require_file(c: Connection, path: str, owner: str = "", group: str = "", mode: str = ""):
    """
    Require a file to exist
    """
    if not is_file(c, path):
        c.run(f"touch {quote(path)}", echo=True)

    _fix_perms(c, path, owner, group, mode)


def _fix_perms(c: Connection, path: str, owner: str, group: str, mode: str):
    # Ensure correct owner
    if (owner and get_owner(c, path) != owner) or (group and get_group(c, path) != group):
        if owner and group:
            c.run(f"chown {owner}:{group} {quote(path)}", echo=True)
        elif owner:
            c.run(f"chown {owner} {quote(path)}", echo=True)
        elif group:
            c.run(f"chgrp {group}:{group} {quote(path)}", echo=True)

    # Ensure correct mode
    if mode and get_mode(c, path).lstrip("0") != mode.lstrip("0"):
        c.run(f"chmod {mode} {quote(path)}", echo=True)


def is_file(c: Connection, path: str):
    """
    Check if a path exists, and is a file.
    """
    return c.run(f"test -f {quote(path)}", warn=True, hide="both").ok


def is_dir(c: Connection, path: str):
    """
    Check if a path exists, and is a directory.
    """
    return c.run(f"test -d {quote(path)}", warn=True, hide="both").ok


def get_owner(c: Connection, path: str):
    """
    Get the owner name of a file or directory.
    """
    result: Result = c.run(f"stat -c %U {quote(path)}", hide="both")
    return result.stdout.strip()


def get_group(c: Connection, path: str):
    """
    Get the group of a file or directory.
    """
    result: Result = c.run(f"stat -c %G {quote(path)}", hide="both")
    return result.stdout.strip()


def get_mode(c: Connection, path: str):
    """
    Get the mode/permissions of a file or directory.
    """
    result: Result = c.run(f"stat -c %a {quote(path)}", hide="both")
    return result.stdout.strip()
