import os.path
from dataclasses import dataclass

from fabric.connection import Connection

from . import files
from .files import get_file_as_bytes, put_file_from_bytes


@dataclass
class Template:
    system: bool
    local_path: str
    remote_path: str
    reload_command: str | None = None
    owner: str | None = None
    mode: str | None = None


def upload_template_and_reload(c: Connection, template: Template, context_data: dict):
    """
    Uploads a template only if it has changed, and if so, reload the
    related service.
    """
    local_path = template.local_path
    if not os.path.exists(local_path):
        project_root = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(project_root, local_path)
    remote_path = template.remote_path
    reload_command = template.reload_command
    remote_data = ""
    if files.exists(c, remote_path):
        remote_data = get_file_as_bytes(c, remote_path).decode("utf-8")

    with open(local_path) as f:
        local_data = f.read()
        local_data %= context_data
    clean = lambda s: s.replace("\n", "").replace("\r", "").strip()
    if clean(remote_data) == clean(local_data):
        return

    put_file_from_bytes(c, remote_path, local_data.encode("utf-8"), mode=template.mode, owner=template.owner)
    if reload_command:
        c.run(reload_command, echo=True)
