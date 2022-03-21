"""
fabfile for deploying and managing cciw.co.uk
"""

import json
import os
import re
import subprocess
import tempfile
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime

import fabtools
from fabric.api import env, hide, local, run, task
from fabric.context_managers import cd, lcd, prefix, settings, shell_env
from fabric.contrib.files import append, exists, upload_template
from fabric.decorators import with_settings
from fabric.operations import get, put

join = os.path.join
rel = lambda *x: os.path.normpath(join(os.path.abspath(os.path.dirname(__file__)), *x))

env.user = "cciw"
if not env.hosts:
    env.hosts = ["cciw.co.uk"]
    # env.hosts = ['cciw2.digitalocean.com']

env.proj_name = "cciw"
env.proj_app = "cciw"  # Python module for project
env.proj_user = env.user

env.domains = ["www.cciw.co.uk"]
env.domains_regex = "|".join(re.escape(d) for d in env.domains)
env.domains_nginx = " ".join(env.domains)

env.locale = "en_GB.UTF-8"
env.num_workers = "3"

# Python version
PYTHON_BIN = "python3.9"
PYTHON_PREFIX = ""  # e.g. /usr/local  Use "" for automatic
PYTHON_FULL_PATH = f"{PYTHON_PREFIX}/bin/{PYTHON_BIN}" if PYTHON_PREFIX else PYTHON_BIN


LOCAL_DB_BACKUPS = rel("..", "db_backups")
LOCAL_USERMEDIA = rel("..", "usermedia")
LOCAL_SECURE_DOWNLOAD_ROOT = rel("..", "secure_downloads_src")

SECRETS_FILE_REL = "config/secrets.json"
NON_VCS_SOURCES = [
    SECRETS_FILE_REL,
]
SECRETS_FILE = rel(".", SECRETS_FILE_REL)

WEBAPPS_ROOT = f"/home/{env.proj_user}/webapps"

CURRENT_VERSION = "current"

REQS = [
    # Daemons
    "ufw",
    # Command line tools which are used non interactively
    "debian-goodies",  # checkrestart
    "software-properties-common",  # "
    "unattended-upgrades",
    "apt-listchanges",
    "rsync",
    "git",
    "mercurial",
    # Tools for interactive use only
    "htop",
    "mosh",
    "net-tools",
    "nmap",
    "silversearcher-ag",
    "git-core",
    "aptitude",
    "ncdu",
    "joe",
    "zsh",
    # Databases/servers
    "postgresql",  # without version numbers, uses the supported version, which is usually fine
    "postgresql-client",
    "postgresql-contrib",
    "memcached",
    # Daemons
    "supervisor",  # For running uwsgi and php-cgi daemons
    "nginx",
    # Non-Python stuff
    "npm",
    "nodejs",  # For less css
    # Python stuff
    "python",
    "python3",
    "python3.9",
    "python3.9-venv",
    # For building Python extensions
    "build-essential",
    "python-dev",
    "python3-dev",
    "python3.9-dev",
    "libpq-dev",  # For psycopg2
    "libxml2-dev",  # For lxml/uwsgi
    "libxslt-dev",  # For lxml/uwsgi
    "libffi-dev",  # For cffi
    # Soft PIL + jpegtran-cffi dependencies
    "libturbojpeg",
    "libjpeg8",
    "libjpeg8-dev",
    "libpng-dev",
    "libfreetype6",
    "libfreetype6-dev",
    "zlib1g",
    "zlib1g-dev",
    # Soft uwsgi requirement (for harakiri alerts)
    "libpcre3-dev",
    # Other
    "certbot",
]


@task
def print_hostname():
    run("hostname")


# Utilities

as_rootuser = with_settings(user="root")


def virtualenv(venv):
    return prefix(f"source {venv}/bin/activate")


@contextmanager
def django_project(target):
    with virtualenv(target.VENV_ROOT), cd(target.SRC_ROOT):
        yield


# Versions and conf:

# Version class encapsulates the fact that on each deploy we create a new
# directory for virtualenv and sources, and after we are done setting it up, we
# switch the 'current' link to the new version.


class Version:
    PROJECT_ROOT_BASE = os.path.join(WEBAPPS_ROOT, env.proj_name)
    VERSIONS_ROOT = os.path.join(PROJECT_ROOT_BASE, "versions")
    MEDIA_ROOT_SHARED = PROJECT_ROOT_BASE + "/usermedia"

    @classmethod
    def current(cls):
        return cls(CURRENT_VERSION)

    def __init__(self, version):
        self.version = version
        self.PROJECT_ROOT = os.path.join(self.VERSIONS_ROOT, version)
        self.SRC_ROOT = os.path.join(self.PROJECT_ROOT, "src")
        self.VENV_ROOT = os.path.join(self.PROJECT_ROOT, "venv")
        # MEDIA_ROOT/STATIC_ROOT -  sync with settings
        self.STATIC_ROOT = os.path.join(self.PROJECT_ROOT, "static")
        self.MEDIA_ROOT = os.path.join(self.PROJECT_ROOT, "usermedia")
        self.SECURE_DOWNLOAD_ROOT = os.path.join(WEBAPPS_ROOT, "secure_downloads_src")

        CONF = secrets()

        db_user = CONF["PRODUCTION_DB_USER"]
        db_password = CONF["PRODUCTION_DB_PASSWORD"]
        db_port = CONF["PRODUCTION_DB_PORT"]

        self.DB = {
            "NAME": CONF["PRODUCTION_DB_NAME"],
            "USER": db_user,
            "PASSWORD": db_password,
            "PORT": db_port,
        }

    def make_dirs(self):
        for d in [self.PROJECT_ROOT, self.MEDIA_ROOT_SHARED]:
            if not exists(d):
                run(f"mkdir -p {d}")
        links = [(self.MEDIA_ROOT, self.MEDIA_ROOT_SHARED)]
        for link, dest in links:
            if not exists(link):
                run(f"ln -s {dest} {link}")

        # Perms for usermedia
        run(f"find {self.MEDIA_ROOT_SHARED} -type d -exec chmod ugo+rx {{}} ';'")


def secrets():
    if not os.path.exists(SECRETS_FILE):
        print("WARNING: missing secrets file")
        return defaultdict(str)
    return json.load(open(SECRETS_FILE))


# System level install
@task
@as_rootuser
def secure(new_user=env.user):
    """
    Minimal security steps for brand new servers.
    Installs system updates, creates new user for future
    usage, and disables password root login via SSH.
    """
    run("apt update -q")
    run("apt upgrade -y -q")
    if not fabtools.user.exists(new_user):
        ssh_keys = [os.path.expandvars("$HOME/.ssh/id_rsa.pub")]
        ssh_keys = list(filter(os.path.exists, ssh_keys))
        fabtools.user.create(new_user, group=new_user, ssh_public_keys=ssh_keys)
    run("sed -i 's:RootLogin yes:RootLogin without-password:' /etc/ssh/sshd_config")
    run("service ssh restart")
    print(f"Security steps completed. Log in to the server as '{new_user}' from now on.")


@task
def provision():
    """
    Installs the base system and Python requirements for the entire server.
    """
    _install_system()
    _install_locales()
    _fix_startup_services()
    run(f"mkdir -p /home/{env.proj_user}/logs")


@as_rootuser
def _install_system():
    # Install system requirements
    update_upgrade()
    apt(" ".join(REQS))
    _add_swap()
    _install_python_minimum()
    _ssl_dhparam()
    run("apt remove snapd")


@as_rootuser
def _add_swap():
    # Needed to compile some things, and for some occassional processes that
    # need a lot of memory.
    if not exists("/swapfile"):
        run("fallocate -l 1G /swapfile")
        run("chmod 600 /swapfile")
        run("mkswap /swapfile")
        run("swapon /swapfile")
        append("/etc/fstab", "/swapfile   none    swap    sw    0   0\n")

    # Change swappiness
    run("sysctl vm.swappiness=10")
    append("/etc/sysctl.conf", "vm.swappiness=10\n")


@as_rootuser
def _ssl_dhparam():
    dhparams = "/etc/nginx/ssl/dhparams.pem"
    if not exists(dhparams):
        d = os.path.dirname(dhparams)
        if not exists(d):
            run(f"mkdir -p {d}")
        run(f"openssl dhparam -out {dhparams} 2048")


def _install_python_minimum():
    run("pip install -U pip virtualenv wheel virtualenvwrapper")


@as_rootuser
def _install_locales():
    # Generate project locale
    locale = env.locale.replace("UTF-8", "utf8")
    with hide("stdout"):
        if locale not in run("locale -a"):
            run(f"locale-gen {env.locale}")
            run(f"update-locale {env.locale}")
            run("service postgresql restart")


@as_rootuser
def _fix_startup_services():
    for service in [
        "supervisor",
        "postgresql",
    ]:
        run(f"update-rc.d {service} defaults")
        run(f"service {service} start")

    for service in [
        "memcached",  # We use our own instance
    ]:
        run(f"update-rc.d {service} disable")
        run(f"service {service} stop")


@as_rootuser
def apt(packages):
    """
    Installs one or more system packages via apt.
    """
    return run("apt install -y -q " + packages)


# Templates

TEMPLATES = {
    "nginx": {
        "system": True,
        "local_path": "config/nginx.conf.template",
        "remote_path": "/etc/nginx/sites-enabled/%(proj_name)s.conf",
        "reload_command": "service nginx reload",
    },
    "supervisor": {
        "system": True,
        "local_path": "config/supervisor.conf.template",
        "remote_path": "/etc/supervisor/conf.d/%(proj_name)s.conf",
        "reload_command": "supervisorctl reread; supervisorctl update",
    },
    "cron": {
        "system": True,
        "local_path": "config/crontab.template",
        "remote_path": "/etc/cron.d/%(proj_name)s",
        "owner": "root",
        "mode": "600",
    },
}


def inject_template(data):
    return {k: v % env if isinstance(v, str) else v for k, v in data.items()}


def get_templates(filter_func=None):
    """
    Returns each of the templates with env vars injected.
    """
    injected = {}
    for name, data in TEMPLATES.items():
        if filter_func is None or filter_func(data):
            injected[name] = inject_template(data)
    return injected


def get_system_templates():
    return get_templates(lambda data: data["system"])


def get_project_templates():
    return get_templates(lambda data: not data["system"])


def upload_template_and_reload(name, target):
    """
    Uploads a template only if it has changed, and if so, reload the
    related service.
    """
    template = get_templates()[name]
    local_path = template["local_path"]
    if not os.path.exists(local_path):
        project_root = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(project_root, local_path)
    remote_path = template["remote_path"]
    reload_command = template.get("reload_command")
    owner = template.get("owner")
    mode = template.get("mode")
    remote_data = ""
    if exists(remote_path):
        with hide("stdout"):
            remote_data = run(f"cat {remote_path}")
    env_data = env.copy()
    env_data.update(target.__dict__)
    with open(local_path) as f:
        local_data = f.read()
        local_data %= env_data
    clean = lambda s: s.replace("\n", "").replace("\r", "").strip()
    if clean(remote_data) == clean(local_data):
        return
    upload_template(local_path, remote_path, env_data, backup=False)
    if owner:
        run(f"chown {owner} {remote_path}")
    if mode:
        run(f"chmod {mode} {remote_path}")
    if reload_command:
        run(reload_command)


# Deploying project - user level


@task
def create_project():
    deploy_system()
    create_databases()


@as_rootuser
def create_databases():
    target = Version.current()
    # Run create user first, because it deletes user as part of process, and we
    # don't want that happening after a DB has been created.
    db = target.DB
    with shell_env(**pg_environ(db)):
        if not db_check_user_exists_remote(db):
            for run_as_postgres, cmd in db_create_user_commands(db):
                pg_run(cmd, run_as_postgres)

    with shell_env(**pg_environ(db)):
        for run_as_postgres, cmd in db_create_commands(db):
            pg_run(cmd, run_as_postgres)


def pg_run(cmd, run_as_postgres):
    with cd("/"):  # suppress "could not change directory" warnings
        if run_as_postgres:
            return run(f"sudo -u postgres {cmd}")
        else:
            return run(cmd)


def pg_local(cmd, run_as_postgres, capture=False):
    with lcd("/"):  # suppress "could not change directory" warnings
        if run_as_postgres:
            retval = local(f"sudo -u postgres {cmd}", capture=capture)
        else:
            retval = local(cmd, capture=capture)
    if capture:
        print(retval)
        print(retval.stderr)
    return retval


@task
@as_rootuser
def deploy_system():
    """
    Deploy system level (root) components.
    """
    target = Version.current()
    for name in get_system_templates():
        upload_template_and_reload(name, target)


@task
def deploy():
    """
    Deploy project.
    """
    check_branch()
    deploy_checks()
    code_quality_checks()
    push_to_central_vcs()
    target = create_target()
    push_sources(target)
    create_venv(target)
    install_requirements(target)
    build_static(target)
    upload_project_templates(target)
    update_database(target)
    make_target_current(target)
    deploy_system()
    restart_all()
    tag_deploy()  # Once 'current' symlink is switched and services are restarted
    copy_protected_downloads(target)
    setup_email_routes(target)
    delete_old_versions()

    # Push tags created in tag_deploy
    push_to_central_vcs()
    # See also logic in settings.py for creating release name
    release = "cciw@" + target.version
    create_sentry_release(release, target.version)


@task
def deploy_checks():
    local("./manage.py check --deploy")


@task
def code_quality_checks():
    """
    Run code quality checks, including tests.
    """
    if getattr(env, "skip_code_quality_checks", False):
        return
    local("flake8 .")
    local("isort -c .")
    local("pytest -m 'not selenium'")


@task
def skip_code_quality_checks():
    env.skip_code_quality_checks = True


def check_branch():
    if local("git rev-parse --abbrev-ref HEAD", capture=True) != "master":
        raise AssertionError("Branch must be 'master' for deploying")


def push_to_central_vcs():
    # This task is designed to fail if it would create multiple heads on
    # central vcs i.e. if central has code on the master branch that hasn't been
    # merged locally. This prevents deploys overwriting a previous deploy
    # unknowingly due to failure to merge changes.
    local("git push origin master")


@task
def no_tag():
    """
    Don't tag deployment in VCS"
    """
    env.no_tag = True


def create_target():
    """
    Creates a place on the server where we will push the app to.
    """
    commit_ref = get_current_git_ref()
    target = Version(commit_ref)
    target.make_dirs()
    return target


def push_sources(target):
    """
    Push source code to server
    """
    ensure_src_dir(target)

    # For speed, we copy from previous dir
    previous_target = get_target_current_version(target)
    target_src_root = target.SRC_ROOT
    previous_src_root = previous_target.SRC_ROOT

    if not exists(os.path.join(target_src_root, ".git")):
        previous_target = get_target_current_version(target)
        previous_src_root = previous_target.SRC_ROOT
        if exists(previous_src_root) and exists(os.path.join(previous_src_root, ".git")):
            # For speed, clone the 'current' repo which will be very similar to
            # what we are pushing.
            run(f"git clone {previous_src_root} {target_src_root}")
            with cd(target_src_root):
                run("git checkout master || git checkout -b master")
        else:
            with cd(target_src_root):
                run("git init")
        with cd(target_src_root):
            run("echo '[receive]' >> .git/config")
            run("echo 'denyCurrentBranch = ignore' >> .git/config")

    local(f"git push ssh://{env.user}@{env.host}/{target_src_root}")
    with cd(target_src_root):
        run(f"git reset --hard {target.version}")

    # Also need to sync files that are not in main sources VCS repo.
    push_non_vcs_sources(target)

    # Need settings file
    with cd(target_src_root):
        run("cp cciw/settings_local_example.py cciw/settings_local.py")


@task
def push_non_vcs_sources(target=None):
    """
    Push non-VCS sources to server
    """
    if target is None:
        target = Version.current()
    for s in NON_VCS_SOURCES:
        local(f"rsync {s} {env.proj_user}@{env.hosts[0]}:{target.SRC_ROOT}/{s}")


@task
def get_non_vcs_sources():
    """
    Pull non-VCS sources (including secrets.json) from server
    """
    target = Version.current()
    for s in NON_VCS_SOURCES:
        local(f"rsync {env.proj_user}@{env.hosts[0]}:{target.SRC_ROOT}/{s} {s}")


def tag_deploy():
    if getattr(env, "no_tag", False):
        return
    local("git tag deploy-production-$(date --iso-8601=seconds | tr ':' '-' | cut -f 1 -d '+')")
    local("git push --tags origin")


def ensure_src_dir(target):
    if not exists(target.SRC_ROOT):
        run(f"mkdir -p {target.SRC_ROOT}")


def push_secrets(target):
    put(SECRETS_FILE, os.path.join(target.SRC_ROOT, "config/secrets.json"))


def create_venv(target):
    """
    Create a Python virtualenv in the target.
    """
    venv_root = target.VENV_ROOT
    if exists(venv_root):
        return

    run(f"virtualenv --python={PYTHON_BIN} {venv_root}")
    run(f"echo {target.SRC_ROOT} > {target.VENV_ROOT}/lib/{PYTHON_BIN}/site-packages/projectsource.pth")


def install_requirements(target):
    if getattr(env, "no_installs", False):
        return

    with django_project(target):
        _install_deps_with(run)


def _install_deps_with(run_with):
    run_with("pip install --progress-bar off --upgrade setuptools pip wheel six")
    run_with("pip install --progress-bar off -r requirements.txt --exists-action w")


def build_static(target):
    assert target.STATIC_ROOT.strip() != "" and target.STATIC_ROOT.strip() != "/"
    with django_project(target):
        # django-compressor doesn't always find changes if we don't do this:
        run("find . -name '*.scss' | xargs touch")
        run("./manage.py collectstatic -v 0 --noinput")

    # This is needed for certbot/letsencrypt:
    run(f"mkdir -p {target.STATIC_ROOT}/root")

    # Permissions
    run(f"chmod -R ugo+r {target.STATIC_ROOT}")


def upload_project_templates(target):
    target = Version.current()
    for name in get_project_templates():
        upload_template_and_reload(name, target)


def update_database(target):
    if getattr(env, "no_db", False):
        return
    with django_project(target):
        if getattr(env, "fake_migrations", False):
            args = "--fake"
        else:
            args = "--fake-initial"
        run(f"./manage.py migrate --noinput {args}")
        run("./manage.py setup_auth_roles")


def setup_email_routes(target):
    with django_project(target):
        run("./manage.py setup_ses_routes")


def copy_protected_downloads(target):
    rsync_dir(LOCAL_SECURE_DOWNLOAD_ROOT, target.SECURE_DOWNLOAD_ROOT)
    run(f"chmod -R ugo+r {target.SECURE_DOWNLOAD_ROOT}")
    run(f"find {target.SECURE_DOWNLOAD_ROOT} -type d | xargs chmod ugo+rx")


def rsync_dir(local_dir, dest_dir):
    # clean first
    with settings(warn_only=True):
        local(f"find -L {local_dir} -name '*.pyc' | xargs rm || true", capture=True)
    local(
        f"rsync -z -r -L --delete --exclude='_build' --exclude='.hg' --exclude='.git' --exclude='.svn' --delete-excluded {local_dir}/ {env.proj_user}@{env.hosts[0]}:{dest_dir}",
        capture=False,
    )


def get_target_current_version(target):
    return target.__class__.current()


def make_target_current(target):
    # Switches synlink for 'current' to point to 'target.PROJECT_ROOT'
    current_target = get_target_current_version(target)
    run(f"ln -snf {target.PROJECT_ROOT} {current_target.PROJECT_ROOT}")


def get_current_git_ref():
    return local("git rev-parse HEAD", capture=True).strip()


@task
def fake_migrations():
    env.fake_migrations = True


@task
def delete_old_versions():
    with cd(Version.VERSIONS_ROOT):
        commitref_glob = "?" * 40
        run(f"ls -dtr {commitref_glob} | head -n -4 | xargs rm -rf")


# --- Managing running system ---


@task
def stop_webserver():
    """
    Stop the webserver that is running the Django instance
    """
    supervisorctl(f"stop {env.proj_name}_uwsgi")


@task
def start_webserver():
    """
    Starts the webserver that is running the Django instance
    """
    supervisorctl(f"start {env.proj_name}_uwsgi")


@task
@as_rootuser
def restart_webserver():
    """
    Gracefully restarts the webserver that is running the Django instance
    """
    pidfile = f"/tmp/{env.proj_name}_uwsgi.pid"
    if exists(pidfile):
        output = run(f"kill -HUP `cat {pidfile}`", warn_only=True)
        if output.failed:
            start_webserver()
    else:
        start_webserver()


@task
def restart_all():
    restart_webserver()


@task
def stop_all():
    stop_webserver()


@task
@as_rootuser
def supervisorctl(*commands):
    run(f"supervisorctl {' '.join(commands)}")


@task
def manage_py_command(*commands):
    target = Version.current()
    with django_project(target):
        run(f"./manage.py {' '.join(commands)}")


@as_rootuser
def update_upgrade():
    run("apt update")
    run("apt upgrade")


@task
def create_sentry_release(version, last_commit):
    local(f"sentry-cli releases --org cciw new -p cciw-website {version}")
    local(f"sentry-cli releases --org cciw set-commits {version} --auto")
    local(f"sentry-cli releases --org cciw finalize {version}")


# -- DB snapshots --


@task
def get_and_load_production_db():
    """
    Dump current production Django DB and load into dev environment
    """
    filename = get_live_db()
    local_restore_from_dump(filename)


@task
def get_live_db():
    print(
        """
IMPORTANT:

It is against CCIW policy to store live data on developers machines due to
privacy and security issues. If this is done, it must only ever be a temporary
measure for debugging an issue that cannot be done any other way, and the data
must be deleted immediately after.
"""
    )
    if input("Are you sue you want to continue? (y/n) ").strip() != "y":
        raise SystemExit()
    filename = dump_db(Version.current())
    local(f"mkdir -p {LOCAL_DB_BACKUPS}")
    return list(get(filename, local_path=LOCAL_DB_BACKUPS + "/%(basename)s"))[0]


@task
def local_restore_from_dump(filename):
    _local_django_setup()
    from django.conf import settings

    db = settings.DATABASES["default"]

    filename = os.path.abspath(filename)
    with shell_env(**pg_environ(db)):
        if not db_check_user_exists_local(db):
            for run_as_postgres, cmd in db_create_user_commands(db):
                pg_local(cmd, run_as_postgres)

        for run_as_postgres, cmd in (
            db_drop_database_commands(db) + db_create_commands(db) + pg_restore_cmds(db, filename)
        ):
            pg_local(cmd, run_as_postgres)


def make_django_db_filename(target):
    return f"/home/{env.user}/db-{target.DB['NAME']}.django.{datetime.now().strftime('%Y-%m-%d_%H.%M.%S')}.pgdump"


def dump_db(target):
    filename = make_django_db_filename(target)
    db = target.DB
    run(f"pg_dump -Fc -U {db['USER']} -O -f {filename} {db['NAME']}")
    return filename


def pg_restore_cmds(db, filename, clean=False):
    return [
        (False, f"pg_restore -h localhost -O -U {db['USER']} {' -c ' if clean else ''} -d {db['NAME']} {filename}"),
    ]


def db_create_user_commands(db):
    return [
        (
            True,
            f"psql -p {db['PORT']} -U postgres -d template1 -c \"CREATE USER {db['USER']} WITH PASSWORD '{db['PASSWORD']}';\" ",
        ),
    ]


def db_check_user_exists_command(db):
    return f"""psql -p {db['PORT']} -U postgres -d postgres -t -c "SELECT COUNT(*) FROM pg_user WHERE usename='{db["USER"]}';" """


def db_check_user_exists_local(db):
    output = pg_local(db_check_user_exists_command(db), True, capture=True).strip()
    return output == "1"


def db_check_user_exists_remote(db):
    output = pg_run(db_check_user_exists_command(db), True).strip()
    return output == "1"


def db_create_commands(db):
    return [
        (
            True,
            f""" psql -p {db['PORT']} -U postgres -d template1 -c " """
            f""" CREATE DATABASE {db['NAME']} """
            f""" TEMPLATE = template0 ENCODING = 'UTF8' LC_CTYPE = '{env.locale}' LC_COLLATE = '{env.locale}';"""
            f""" " """,
        ),
        (
            True,
            f"psql -p {db['PORT']} -U postgres -d template1 -c \"GRANT ALL ON DATABASE {db['NAME']} TO {db['USER']};\" ",
        ),
        (True, f"psql -p {db['PORT']} -U postgres -d template1 -c \"ALTER USER {db['USER']} CREATEDB;\" "),
    ]


def db_drop_database_commands(db):
    return [
        (True, f"psql -p {db['PORT']} -U postgres -d template1 -c \"DROP DATABASE IF EXISTS {db['NAME']};\" "),
    ]


def db_restore_commands(db, filename):
    return (
        db_drop_database_commands(db)
        + db_create_user_commands(db)
        + db_create_commands(db)
        + pg_restore_cmds(db, filename)
    )


PG_ENVIRON_MAP = {
    "NAME": "PGDATABASE",
    "HOST": "PGHOST",
    "PORT": "PGPORT",
    "USER": "PGUSER",
    "PASSWORD": "PGPASSWORD",
}


def pg_environ(db):
    """
    Returns the environment variables postgres command line tools like psql
    and pg_dump use as a dict, ready for use with Fabric's shell_env.
    """
    return {PG_ENVIRON_MAP[name]: str(val) for name, val in db.items() if name in PG_ENVIRON_MAP}


@as_rootuser
def db_restore(db, filename):
    with shell_env(**pg_environ(db)):
        if not db_check_user_exists_remote(db):
            for run_as_postgres, cmd in db_create_user_commands(db):
                pg_run(cmd, run_as_postgres)

        for run_as_postgres, cmd in (
            db_drop_database_commands(db) + db_create_commands(db) + pg_restore_cmds(db, filename)
        ):
            pg_run(cmd, run_as_postgres)


@task
def migrate_upload_db(local_filename):
    stop_all()
    local_filename = os.path.normpath(os.path.abspath(local_filename))
    remote_filename = f"/home/{env.proj_user}/{os.path.basename(local_filename)}"
    put(local_filename, remote_filename)
    target = Version.current()
    db_restore(target.DB, remote_filename)


# -- User media --


@task
def upload_usermedia():
    """
    Upload locally stored usermedia (e.g. booking forms) to the live site.
    """
    target = Version.current()
    local(
        f"rsync -z -r --progress {LOCAL_USERMEDIA}/ {env.proj_user}@{env.hosts[0]}:{target.MEDIA_ROOT}", capture=False
    )
    run(f"find -L {target.MEDIA_ROOT} -type f -exec chmod ugo+r {{}} ';'")
    run(f"find {target.MEDIA_ROOT_SHARED} -type d -exec chmod ugo+rx {{}} ';'")


@task
def download_usermedia():
    target = Version.current()
    local(f"rsync -z -r  {env.proj_user}@{env.hosts[0]}:{target.MEDIA_ROOT}/ {LOCAL_USERMEDIA}", capture=False)


# --- SSL ---


@task
@as_rootuser
def install_or_renew_ssl_certificate():
    version = Version.current()
    certbot_static_path = version.STATIC_ROOT + "/root"
    run(f"test -d {certbot_static_path} || mkdir {certbot_static_path}")
    run(f"letsencrypt certonly --webroot -w {certbot_static_path} -d {env.domains[0]}")
    run("service nginx reload")


@task
def download_letsencrypt_conf():
    local(f"rsync -r -l root@{env.hosts[0]}:/etc/letsencrypt/ config/letsencrypt/")


@task
def upload_letsencrypt_conf():
    local(f"rsync -r -l config/letsencrypt/ root@{env.hosts[0]}:/etc/letsencrypt/")


# ---- ngrok -----

NGROK_1 = "1"
NGROK_2 = "2"


def get_ngrok_version():
    ngrok_version = subprocess.check_output(["ngrok", "version"]).decode("utf-8")
    if ngrok_version.startswith("1."):
        return NGROK_1
    else:
        return NGROK_2  # Assume anything more recent is compatible with version 2


@task
def run_ngrok(port=8002):
    """
    Launch ngrok, and update Site record to match the URL.
    """
    # We don't want to interfere with ngrok input/output/screen use, so we fork
    # using exec. However, we do need to know what is going on in order know the
    # URL, so we spawn another fab task that monitors a log file

    # Check that this works first, so that set_site_from_url doesn't fail silently
    import django

    django.setup()

    # Need a logfile
    log_fd, log_filename = tempfile.mkstemp()
    os.close(log_fd)

    # launch fab in separate process in background.
    os.spawnv(os.P_NOWAIT, "/bin/sh", ["sh", "-c", f"fab ngrok_helper:{log_filename} > /dev/null 2> /dev/null"])

    # Now launch ngrok, replacing current process
    ngrokpath = _get_path("ngrok")

    if get_ngrok_version() == NGROK_1:
        os.execv(ngrokpath, ["ngrok", f"--log={log_filename}", str(port)])
    else:
        os.execv(ngrokpath, ["ngrok", "http", str(port), "--log-level", "debug", "--log", log_filename])


NGROK_LOG_MATCHERS = {
    NGROK_1: {
        "url": r"\[client\] Tunnel established at ([^ ]*)",
        "shutdown": r"\[controller\] Shutting down",
    },
    NGROK_2: {
        "url": 'msg="decoded response".* URL:([^ ]*)',
        "shutdown": 'msg="all component stopped"',
    },
}


@task
def ngrok_helper(log_filename):
    matchers = NGROK_LOG_MATCHERS[get_ngrok_version()]

    f = open(log_filename)
    while True:
        line = f.readline()
        if line:
            m = re.search(matchers["url"], line.strip())
            if m:
                set_site_from_url(m.groups()[0])
            if re.search(matchers["shutdown"], line):
                break
        else:
            time.sleep(0.5)
    os.unlink(log_filename)


def _get_path(program_name):
    return subprocess.check_output(["which", program_name]).strip()


@task
def set_site_from_url(url):
    _local_django_setup()
    from urllib.parse import urlparse

    from django.contrib.sites.models import Site

    parts = urlparse(url)
    Site.objects.all().update(domain=parts.netloc)


def _local_django_setup():
    os.environ["DJANGO_SETTINGS_MODULE"] = "cciw.settings_local"
    import django

    django.setup()


# --- developer setup ---
@task
def initial_dev_setup():
    local("cp cciw/settings_local_example.py cciw/settings_local.py")
    if "VIRTUAL_ENV" not in os.environ:
        raise AssertionError("You need to set up a virtualenv before using this")
    if not os.path.exists(LOCAL_SECURE_DOWNLOAD_ROOT):
        local(f"mkdir -p {LOCAL_SECURE_DOWNLOAD_ROOT}")
    if not os.path.exists("../logs"):
        local("mkdir ../logs")
    _install_deps_local()
    get_non_vcs_sources()


def _install_deps_local():
    _install_deps_with(local)
