import json
import os.path
import re
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from functools import partial
from shlex import quote

from fabric.connection import Connection
from fabric.transfer import Transfer
from fabutils import apt, disks, files, locales, postgresql, ssh, ssl, users
from fabutils.connections import local_task, managed_connection_task
from fabutils.templates import Template, upload_template_and_reload

Database = postgresql.Database

# -- Constants

DEFAULT_HOST = "cciw.co.uk"
PROJECT_USER = "cciw"
DEFAULT_USER = PROJECT_USER
PROJECT_PYTHON_MODULE = "cciw"

PROJECT_NAME = "cciw"

PROJECT_LOCALE = "en_GB.UTF-8"


PYTHON_BIN = "python3.13"  # See also packages below
PYTHON_PREFIX = ""  # e.g. /usr/local.  Use "" for automatic
PYTHON_FULL_PATH = f"{PYTHON_PREFIX}/bin/{PYTHON_BIN}" if PYTHON_PREFIX else PYTHON_BIN

join = os.path.join
rel = lambda *x: os.path.normpath(join(os.path.abspath(os.path.dirname(__file__)), *x))

LOCAL_DB_BACKUPS = rel("..", "db_backups")
LOCAL_APP_DATA = rel("..", "app_data")
LOCAL_USERMEDIA = rel("..", "usermedia")
LOCAL_SECURE_DOWNLOAD_ROOT = rel("..", "secure_downloads_src")

SECRETS_FILE_REL = "config/secrets.json"
NON_VCS_SOURCES = [
    SECRETS_FILE_REL,
]
SECRETS_FILE = rel(".", SECRETS_FILE_REL)

WEBAPPS_ROOT = f"/home/{PROJECT_USER}/webapps"

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
    "wajig",
    # Databases/servers
    "postgresql",  # without version numbers, uses the supported version, which is usually fine
    "postgresql-client",
    "postgresql-contrib",
    "memcached",
    # Daemons
    "supervisor",  # For running gunicorn and php-cgi daemons
    "nginx",
    # Python stuff - currently just for install uv, which then installs everything else.
    "python3.12",
    "python3.12-venv",
    "python3-pip",
    "pipx",
    # For building Python extensions
    "build-essential",
    "python3-dev",
    "python3.12-dev",
    "libpq-dev",  # For psycopg2
    "libxml2-dev",  # For lxml
    "libxslt-dev",  # For lxml
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
    # for pango, weasyprint
    "libpangocairo-1.0-0",
    # Other
    "certbot",
    "bogofilter",
]


TEMPLATES = [
    Template(
        system=True,
        local_path="config/nginx.conf.template",
        remote_path=f"/etc/nginx/sites-enabled/{PROJECT_NAME}.conf",
        reload_command="service nginx reload",
    ),
    Template(
        system=True,
        local_path="config/supervisor.conf.template",
        remote_path=f"/etc/supervisor/conf.d/{PROJECT_NAME}.conf",
        reload_command="supervisorctl reread; supervisorctl update",
    ),
    Template(
        system=True,
        local_path="config/gunicorn_logging.conf.template",
        remote_path="/etc/gunicorn_logging.conf",
    ),
    Template(
        system=True,
        local_path="config/crontab.template",
        remote_path=f"/etc/cron.d/{PROJECT_NAME}",
        owner="root",
        mode="600",
    ),
]


IS_STAGING = False  # Can be changed by ``staging`` task


def get_domain():
    # This is similar to code in settings.py
    return "staging.cciw.co.uk" if IS_STAGING else "www.cciw.co.uk"


def get_template_context():
    return {
        "DOMAIN_REGEX": re.escape(get_domain()),
        "DOMAIN": get_domain(),
        "LOCALE": PROJECT_LOCALE,
        "PROJECT_PYTHON_MODULE": PROJECT_PYTHON_MODULE,
        "PROJECT_USER": PROJECT_USER,
        "PROJECT_NAME": PROJECT_NAME,
    }


def get_system_templates() -> list[Template]:
    return [template for template in TEMPLATES if template.system]


def get_project_templates() -> list[Template]:
    return [template for template in TEMPLATES if not template.system]


# -- My decorators

task = managed_connection_task(DEFAULT_USER, DEFAULT_HOST)
root_task = managed_connection_task("root", DEFAULT_HOST)


# -- System level provisioning


@task()
def staging(c):
    """
    Set config tweaks appropriate for staging environment
    """
    global IS_STAGING
    IS_STAGING = True


@root_task()
def initial_secure(c):
    """
    Lock down server and secure. Run this after creating new server.
    """
    apt.update_upgrade(c)
    ssh.disable_root_login_with_password(c)
    print("Security steps completed.")


@root_task()
def provision(c):
    """
    Installs the base system and Python requirements for the entire server.
    """
    locales.install(c, PROJECT_LOCALE)
    _install_system(c)
    _fix_startup_services(c)


@root_task()
def install_apt_requirements(c):
    apt.update_upgrade(c)
    apt.install(c, REQS)


def _install_system(c: Connection):
    # Install system requirements
    install_apt_requirements(c)
    # Remove some bloat:
    apt.remove(c, ["snapd"])
    disks.add_swap(c, size="1G", swappiness="10")
    # We will use uv to install everything else
    c.run("pipx install uv", echo=True)
    ssl.generate_ssl_dhparams(c)


def _fix_startup_services(c: Connection):
    for service in [
        "supervisor",
        "postgresql",
    ]:
        c.run(f"update-rc.d {service} defaults", echo=True)
        c.run(f"service {service} start", echo=True)

    for service in [
        "memcached",  # We use our own instance
    ]:
        c.run(f"update-rc.d {service} disable", echo=True)
        c.run(f"service {service} stop", echo=True)


# -- Project level deployment

# Versions and conf:

# Version class encapsulates the fact that on each deploy we create a new
# directory for virtualenv and sources, and after we are done setting it up, we
# switch the 'current' link to the new version.


class Version:
    PROJECT_ROOT_BASE = os.path.join(WEBAPPS_ROOT, PROJECT_NAME)
    VERSIONS_ROOT = os.path.join(PROJECT_ROOT_BASE, "versions")
    MEDIA_ROOT_SHARED = PROJECT_ROOT_BASE + "/usermedia"

    @classmethod
    def current(cls):
        """
        Create target representing the current (normally already deployed) version
        """
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

        self.DB: Database = Database(
            name=CONF["PRODUCTION_DB_NAME"],
            user=CONF["PRODUCTION_DB_USER"],
            password=CONF["PRODUCTION_DB_PASSWORD"],
            port=CONF["PRODUCTION_DB_PORT"],
            locale=PROJECT_LOCALE,
        )

    def make_dirs(self, c: Connection):
        for dirname in [self.PROJECT_ROOT, self.MEDIA_ROOT_SHARED, self.SRC_ROOT]:
            files.require_directory(c, dirname)
        links = [(self.MEDIA_ROOT, self.MEDIA_ROOT_SHARED)]
        for link, dest in links:
            if not files.exists(c, link):
                c.run(f"ln -s {quote(dest)} {quote(link)}")

        # Perms for usermedia
        c.run(f"find {quote(self.MEDIA_ROOT_SHARED)} -type d -exec chmod ugo+rx {{}} ';'")

    def project_run(self, c: Connection, cmd: str, **kwargs):
        with c.cd(self.SRC_ROOT), c.prefix(f"source {self.VENV_ROOT}/bin/activate"):
            env = kwargs.pop("env", {})
            env["UV_PROJECT_ENVIRONMENT"] = self.VENV_ROOT
            kwargs["env"] = env
            return c.run(cmd, **kwargs)


def secrets():
    if not os.path.exists(SECRETS_FILE):
        print("WARNING: missing secrets file")
        return defaultdict(str)
    return json.load(open(SECRETS_FILE))


# -- Start project level tasks ---


@task()
def create_project(c):
    """
    Initial project level setup, only needs to be run once
    """
    # create_project_user has to come before `deploy_system`
    # because system level config refers to this user
    create_project_user(c)
    deploy_system(c)
    create_databases(c)


@root_task()
def create_project_user(c):
    if not users.user_exists(c, PROJECT_USER):
        ssh_keys = [os.path.expandvars("$HOME/.ssh/id_rsa.pub")]
        users.create_user(c, PROJECT_USER, ssh_public_keys=ssh_keys)
        files.require_directory(c, f"/home/{PROJECT_USER}/logs", owner=PROJECT_USER, group=PROJECT_USER)


@root_task()
def create_databases(c):
    target = Version.current()
    db = target.DB
    if not postgresql.check_user_exists(c, db, db.user):
        postgresql.create_default_user(c, db)
    if not postgresql.check_database_exists(c, db):
        postgresql.create_db(c, db)


@root_task()
def deploy_system(c):
    """
    Deploy system level (root) components.
    """
    target = Version.current()
    for template in get_system_templates():
        context_data = get_template_context() | target.__dict__
        upload_template_and_reload(c, template, context_data)


@task()
def deploy(c, skip_tests=False, test_host=False):
    """
    Deploy project.
    """
    if IS_STAGING:
        test_host = True
    if not test_host:
        check_branch(c)
    check_sentry_auth(c)
    deploy_checks(c)
    if not skip_tests:
        run_tests(c)
    if not test_host:
        push_to_central_vcs(c)
    target = create_target(c)
    push_sources(c, target)
    create_venv(c, target)
    install_requirements(c, target)
    build_static(c, target)
    upload_project_templates(c, target)

    # The next group ideally happen as close together as possible,
    # as delays can result in crashes due to DB schema differences
    update_database(c, target)
    make_target_current(c, target)
    deploy_system(c)
    restart_all(c)

    # The next group should be done promptly, but less urgency is needed
    copy_protected_downloads(c, target)
    if not test_host:
        setup_email_routes(c, target)

    # Deployment to the machine is now complete.
    # Post deploy tasks:
    if not test_host:
        tag_deploy(c)
        delete_old_versions(c)

        # Push tags created in tag_deploy
        push_to_central_vcs(c)
        # See also logic in settings.py for creating release name
        release = "cciw@" + target.version
        create_sentry_release(c, release, target.version)


@task()
def deploy_checks(c):
    c.local("./manage.py check --deploy", echo=True, pty=True)
    # setup_auth_roles check is not implemented as a Django check because of
    # dependencies on ContentType being set up and migrations being
    # run in production, nor as a test for the same reason.
    # Here we are assuming that the local DB already has migrations applied
    # and so has ContentType set up correctly.
    c.local("./manage.py setup_auth_roles --check-only", echo=True, pty=True)
    c.local(
        "./manage.py makemigrations --check accounts cciwmain sitecontent officers utils bookings mail contact_us data_retention",
        echo=True,
        pty=True,
    )


@task()
def run_tests(c):
    """
    Run tests and other code quality checks
    """
    c.local("pre-commit run ruff --all-files", echo=True)
    c.local("pytest", echo=True, pty=True)


def check_branch(c: Connection):
    if c.local("git rev-parse --abbrev-ref HEAD").stdout.strip() != "master":
        raise AssertionError("Branch must be 'master' for deploying")


def check_sentry_auth(c: Connection):
    if "SENTRY_AUTH_TOKEN" not in os.environ:
        raise AssertionError("SENTRY_AUTH_TOKEN not found in environment, see notes in development_setup.rst")


def push_to_central_vcs(c: Connection):
    # This task is designed to fail if it would create multiple heads on
    # central vcs i.e. if central has code on the master branch that hasn't been
    # merged locally. This prevents deploys overwriting a previous deploy
    # unknowingly.
    c.local("git push origin master", echo=True)


def create_target(c: Connection):
    """
    Creates a place on the server where we will push the app to.
    """
    commit_ref = get_current_git_ref(c)
    target = Version(commit_ref)
    target.make_dirs(c)
    return target


def push_sources(c: Connection, target: Version):
    """
    Push source code to server
    """
    # For speed, we copy from previous dir
    target_src_root = target.SRC_ROOT

    if not files.exists(c, os.path.join(target_src_root, ".git")):
        previous_target = target.current()
        previous_src_root = previous_target.SRC_ROOT
        if files.exists(c, previous_src_root) and files.exists(c, os.path.join(previous_src_root, ".git")):
            # For speed, clone the 'current' repo which will be very similar to
            # what we are pushing.
            c.run(f"git clone {previous_src_root} {target_src_root}", echo=True)
            with c.cd(target_src_root):
                c.run("git checkout master || git checkout -b master", echo=True)
        else:
            with c.cd(target_src_root):
                c.run("git config --global init.defaultBranch master", echo=True)
                c.run("git init", echo=True)
        with c.cd(target_src_root):
            c.run("echo '[receive]' >> .git/config", echo=True)
            c.run("echo 'denyCurrentBranch = ignore' >> .git/config", echo=True)

    c.local(f"git push ssh://{c.user}@{c.host}/{target_src_root}", echo=True)
    with c.cd(target_src_root):
        c.run(f"git reset --hard {target.version}", echo=True)

    # Also need to sync files that are not in main sources VCS repo.
    push_non_vcs_sources(c, target)

    # Need settings file
    with c.cd(target_src_root):
        c.run("cp cciw/settings_local_example.py cciw/settings_local.py", echo=True)


@task()
def push_non_vcs_sources(c, target=None):
    """
    Push non-VCS sources to server
    """
    if target is None:
        target = Version.current()
    for src in NON_VCS_SOURCES:
        c.local(f"rsync {src} {c.user}@{c.host}:{target.SRC_ROOT}/{src}", echo=True)


@task()
def get_non_vcs_sources(c):
    """
    Pull non-VCS sources (including secrets.json) from server
    """
    target = Version.current()
    for src in NON_VCS_SOURCES:
        c.local(f"rsync {c.user}@{c.host}:{target.SRC_ROOT}/{src} {src}", echo=True)


def tag_deploy(c: Connection):
    c.local("git tag deploy-production-$(date --iso-8601=seconds | tr ':' '-' | cut -f 1 -d '+')", echo=True)
    c.local("git push --tags origin", echo=True)


def push_secrets(c, target):
    Transfer(c).put(
        local=SECRETS_FILE, remote=os.path.join(target.SRC_ROOT, "config/secrets.json"), preserve_mode=False
    )


def create_venv(c, target):
    """
    Create a Python virtualenv in the target.
    """
    venv_root = target.VENV_ROOT
    if files.exists(c, venv_root):
        return

    c.run("pipx install uv")
    c.run("pipx upgrade uv")
    c.run("pipx ensurepath")
    c.run(f"uv python install {PYTHON_BIN}", echo=True)
    c.run(f"uv venv --seed --python={PYTHON_BIN} {venv_root}", echo=True)
    c.run(f"echo {target.SRC_ROOT} > {target.VENV_ROOT}/lib/{PYTHON_BIN}/site-packages/projectsource.pth", echo=True)


def install_requirements(c: Connection, target: Version):
    install_requirements_with(partial(target.project_run, c))


def install_requirements_with(run_command: Callable):
    run_command("uv sync --no-progress", echo=True)


def build_static(c: Connection, target: Version):
    assert target.STATIC_ROOT.strip() != "" and target.STATIC_ROOT.strip() != "/"
    target.project_run(c, "./manage.py collectstatic -v 0 --noinput", echo=True)

    # This is needed for certbot/letsencrypt:
    files.require_directory(c, f"{target.STATIC_ROOT}/root")

    # Permissions
    c.run(f"chmod -R ugo+r {target.STATIC_ROOT}")


def upload_project_templates(c: Connection, target: Version):
    target = Version.current()
    for template in get_project_templates():
        context_data = get_template_context() | target.__dict__
        upload_template_and_reload(c, template, context_data)


def update_database(c: Connection, target: Version, *, fake_migrations: bool = False):
    if fake_migrations:
        args = "--fake"
    else:
        args = "--fake-initial"
    target.project_run(c, f"./manage.py migrate --noinput {args}", echo=True)
    target.project_run(c, "./manage.py setup_auth_roles", echo=True)


def setup_email_routes(c: Connection, target: Version):
    target.project_run(c, "./manage.py setup_ses_routes")


def copy_protected_downloads(c: Connection, target: Version):
    rsync_dir(c, LOCAL_SECURE_DOWNLOAD_ROOT, target.SECURE_DOWNLOAD_ROOT)
    c.run(f"chmod -R ugo+r {target.SECURE_DOWNLOAD_ROOT}")
    c.run(f"find {target.SECURE_DOWNLOAD_ROOT} -type d | xargs chmod ugo+rx")


def rsync_dir(c: Connection, local_dir: str, dest_dir: str):
    # clean first
    c.local(f"find -L {local_dir} -name '*.pyc' | xargs rm || true", hide="both", warn=True)
    c.local(
        f"rsync -z -r -L --delete --exclude='_build' --exclude='.hg' --exclude='.git' --exclude='.svn' --delete-excluded {local_dir}/ {c.user}@{c.host}:{dest_dir}",
    )


def make_target_current(c: Connection, target: Version):
    # Switches synlink for 'current' to point to 'target.PROJECT_ROOT'
    current_target = target.current()
    c.run(f"ln -snf {target.PROJECT_ROOT} {current_target.PROJECT_ROOT}")


def get_current_git_ref(c: Connection):
    return c.local("git rev-parse HEAD").stdout.strip()


@task()
def delete_old_versions(c):
    with c.cd(Version.VERSIONS_ROOT):
        commitref_glob = "?" * 40
        c.run(f"ls -dtr {commitref_glob} | head -n -4 | xargs rm -rf")


def create_sentry_release(c: Connection, version: str, last_commit: str):
    c.local(f"sentry-cli releases --org cciw new -p cciw-website {version}")
    c.local(f"sentry-cli releases --org cciw set-commits {version} --auto")
    c.local(f"sentry-cli releases --org cciw finalize {version}")


# --- Managing running system ---


@root_task()
def stop_webserver(c):
    """
    Stop the webserver that is running the Django instance
    """
    supervisorctl(c, f"stop {PROJECT_NAME}_gunicorn", ignore_errors="no such process")


@root_task()
def start_webserver(c):
    """
    Starts the webserver that is running the Django instance
    """
    supervisorctl(c, f"start {PROJECT_NAME}_gunicorn", ignore_errors="already started")


@root_task()
def restart_webserver(c):
    """
    Gracefully restarts the webserver that is running the Django instance
    """
    # We don't use `kill -HUP` against the pidfile, as it seems
    # to be introduce bugs - gunicorn keeps working in the old directory I think?
    supervisorctl(c, f"restart {PROJECT_NAME}_gunicorn", ignore_errors="already started")


@root_task()
def stop_task_queue(c: Connection):
    supervisorctl(c, f"stop {PROJECT_NAME}_django_q")


@root_task()
def restart_task_queue(c: Connection):
    """
    Restarts the task queue workers
    """
    supervisorctl(c, f"restart {PROJECT_NAME}_django_q")


@root_task()
def restart_all(c):
    supervisorctl(c, "reread")  # for first time, to ensure it can see webserver conf
    restart_webserver(c)
    restart_task_queue(c)


@root_task()
def stop_all(c):
    supervisorctl(c, "stop all")


@root_task()
def start_all(c):
    supervisorctl(c, "start all")


@root_task()
def supervisorctl(c, command, ignore_errors=None):
    result = c.run(f"supervisorctl {command}", echo=True, warn=True, pty=True)
    if result.failed:
        if ignore_errors and any(err in result.stdout or err in result.stderr for err in ignore_errors):
            pass
        else:
            raise RuntimeError(result.stderr)


@task()
def manage_py_command(c, command):
    target = Version.current()
    target.project_run(c, f"./manage.py {command}", echo=True, pty=True)


@task()
def remote_ipython_shell(c):
    target = Version.current()
    target.project_run(c, "./manage.py shell", echo=True, pty=True)


# -- Local utilities


def _local_django_setup():
    os.environ["DJANGO_SETTINGS_MODULE"] = "cciw.settings_local"
    import django

    django.setup()


# -- User media and other files --


@task()
def download_app_data(c):
    """
    Download app data not stored in the main DB
    """
    c.local(f"mkdir -p {LOCAL_APP_DATA}")
    download_bogofilter_data(c)
    download_usermedia(c)


@task()
def upload_app_data(c):
    """
    Upload app data not stored in the main DB, from local copy downloaded previously
    """
    upload_bogofilter_data(c)
    upload_usermedia(c)


@task()
def download_bogofilter_data(c):
    bogofilter_dir = _get_bogofilter_dir(c)
    c.local(f"rsync -z -r {PROJECT_USER}@{c.host}:{bogofilter_dir}/ {LOCAL_APP_DATA}/bogofilter/", echo=True)


@task()
def upload_bogofilter_data(c):
    if os.path.exists(f"{LOCAL_APP_DATA}/bogofilter"):
        bogofilter_dir = _get_bogofilter_dir(c)
        c.local(f"rsync -z -r {LOCAL_APP_DATA}/bogofilter/ {PROJECT_USER}@{c.host}:{bogofilter_dir}/", echo=True)


def _get_bogofilter_dir(c):
    target = Version.current()
    return target.project_run(
        c, "./manage.py shell -c 'from django.conf import settings; print(settings.BOGOFILTER_DIR)'", hide="both"
    ).stdout.strip()


@task()
def download_usermedia(c):
    target = Version.current()
    c.local(f"rsync -z -r {PROJECT_USER}@{c.host}:{target.MEDIA_ROOT}/ {LOCAL_USERMEDIA}", echo=True)


@task()
def upload_usermedia(c):
    """
    Upload locally stored usermedia (e.g. booking forms) to the live site.
    """
    target = Version.current()
    c.local(f"rsync -z -r --progress {LOCAL_USERMEDIA}/ {PROJECT_USER}@{c.host}:{target.MEDIA_ROOT}", echo=True)
    c.run(f"find -L {target.MEDIA_ROOT} -type f -exec chmod ugo+r {{}} ';'", echo=True)
    c.run(f"find {target.MEDIA_ROOT_SHARED} -type d -exec chmod ugo+rx {{}} ';'", echo=True)


# --- SSL ---


@root_task()
def install_or_renew_ssl_certificate(c):
    version = Version.current()
    certbot_static_path = version.STATIC_ROOT + "/root"
    files.require_directory(c, certbot_static_path)
    c.run(f"letsencrypt certonly --webroot -w {certbot_static_path} -d {get_domain()}", echo=True)
    c.run("service nginx reload", echo=True)


@root_task()
def download_letsencrypt_conf(c):
    c.local(f"rsync -r -l root@{c.host}:/etc/letsencrypt/ config/letsencrypt/", echo=True)


@root_task()
def upload_letsencrypt_conf(c):
    c.local(f"rsync -r -l config/letsencrypt/ root@{c.host}:/etc/letsencrypt/", echo=True)


# -- DB snapshots --


@task()
def get_and_load_production_db(c):
    """
    Dump current production Django DB and load into dev environment
    """
    filename = get_live_db(c)
    local_restore_db_from_dump(c, filename)


@task()
def get_live_db(c):
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
    filename = dump_db(c, Version.current().DB)
    c.local(f"mkdir -p {LOCAL_DB_BACKUPS}")
    print(f"Downloading {filename} to {LOCAL_DB_BACKUPS} ...")
    return Transfer(c).get(remote=filename, local=LOCAL_DB_BACKUPS + "/{basename}").local


@local_task()
def local_restore_db_from_dump(c, filename):
    db = _local_db_obj()
    filename = os.path.abspath(filename)
    # We don't use fabutils postgresql commands because they assume postgres is
    # running as global service, and that doesn't seem to work when running with devbox
    c.run("devbox run create_dev_db", echo=True)
    postgresql.restore_db(c, db, filename)


def _local_db_obj():
    _local_django_setup()
    from django.conf import settings

    db_settings = settings.DATABASES["default"]
    db = Database(
        name=db_settings["NAME"],
        user=db_settings["USER"],
        password=db_settings["PASSWORD"],
        port=db_settings["PORT"],
        locale=PROJECT_LOCALE,
    )
    return db


@local_task()
def local_db_dump(c, filename):
    db = _local_db_obj()
    filename = os.path.abspath(filename)
    dump_db(c, db, filename=filename)


def make_django_db_filename(db: Database):
    return f"/home/{PROJECT_USER}/db-{db.name}.django.{datetime.now().strftime('%Y-%m-%d_%H.%M.%S')}.pgdump"


def dump_db(c: Connection, db: Database, filename: str = ""):
    if filename == "":
        filename = make_django_db_filename(db)
    c.run(f"pg_dump -Fc -U {db.user} -O -f {filename} {db.name}", echo=True)
    return filename


@root_task()
def remote_restore_db_from_dump(c, db, filename):
    """
    Perform database restore on remote system
    """
    if not postgresql.check_user_exists(c, db, db.user):
        postgresql.create_default_user(c, db)
    postgresql.drop_db_if_exists(c, db)
    postgresql.create_db(c, db)
    postgresql.restore_db(c, db, filename)


@root_task()
def migrate_upload_db(c, local_filename):
    local_filename = os.path.normpath(os.path.abspath(local_filename))
    remote_filename = f"/home/{PROJECT_USER}/{os.path.basename(local_filename)}"
    files.put(c, local_filename, remote_filename)
    target = Version.current()
    remote_restore_db_from_dump(c, target.DB, remote_filename)


# --- developer setup ---
@task()
def initial_dev_setup(c):
    if "VIRTUAL_ENV" not in os.environ:
        raise AssertionError("You need to set up a virtualenv before using this")
    if not os.path.exists("cciw/settings_local.py"):
        c.local("cp cciw/settings_local_example.py cciw/settings_local.py")
    if not os.path.exists(LOCAL_SECURE_DOWNLOAD_ROOT):
        c.local(f"mkdir -p {LOCAL_SECURE_DOWNLOAD_ROOT}")
    if not os.path.exists("../logs"):
        c.local("mkdir ../logs")
    get_non_vcs_sources(c)


# -- DEBUG


@task()
def hostname(c):
    """Print user and hostname on remote host"""
    c.run("echo $(whoami) @ $(hostname)", echo=True)


@root_task()
def root_hostname(c):
    c.run("echo $(whoami) @ $(hostname)", echo=True)


@task()
def check_user_exists(c, username):
    """
    Checks that a system user exists
    """
    print(users.user_exists(c, username))


@task()
def test_multiple(c):
    root_hostname(c)
    root_hostname(c)
    root_hostname(c)
    root_hostname(c)


@root_task()
def test_db_user_exists(c, username):
    target = Version.current()
    print(postgresql.check_user_exists(c, target.DB, username))


@task()
def run_psql(c, sql):
    postgresql.PsqlCommand(sql=sql, db=Version.current().DB).execute(c, hide=None)


@task()
def get_file_owner(c, path):
    print(files.get_owner(c, path))


@task()
def test_require_file(c, path, mode="0700", owner=""):
    files.require_file(c, path, mode=mode, owner=owner)


@root_task()
def test_home_directory(c, user):
    print(users.home_directory(c, user))


@task()
def test_local_task(c):
    my_local_task(c)


@local_task()
def my_local_task(c):
    c.run("hostname")


@root_task()
def check_db_exists(c):
    print(postgresql.check_database_exists(c, Version.current().DB))
