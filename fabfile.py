import os
import os.path
import sys

from datetime import datetime
from fabric.api import run, local, env, get, task
from fabric.contrib.files import exists
from fabric.contrib import console
from fabric.context_managers import cd, lcd, settings
import psutil
import re
import subprocess
import tempfile
import time

join = os.path.join


#  fabfile for deploying CCIW
#
# == Overview ==
#
# === Development ===
#
# You need a root directory to hold everything, and the following
# sub directories:
#
#  src/    - holds a checkout of this repository
#            i.e. fabfile.py and siblings live in that dir.
#
#  usermedia/  - corresponds to MEDIA_ROOT
#
#  secure_downloads/     - corresponds to SECUREDOWNLOAD_SERVE_ROOT
#
#  secure_downloads_src/ - corresponds to SECUREDOWNLOAD_SOURCE
#
# === Deployment ===
#
# There are two targets, STAGING and PRODUCTION, which live on the same
# server. They are almost identical, with these differences:
# - STAGING is on staging.cciw.co.uk
# - PRODUCTION is on www.cciw.co.uk
# - They have different databases
# - They have different apps on the webfaction server
#    - for the django project app
#    - for the static app
# - STAGING has SSL turned off.
#
# settings_priv.py and settings.py controls these things.

# The information about this layout is unfortunately spread around a couple of
# places - this file and the settings file - because it is needed in both at
# different times.

rel = lambda *x: join(os.path.abspath(os.path.dirname(__file__)), *x)

USER = 'cciw'
HOST = 'cciw.co.uk'
APP_NAME = 'cciw'

# Host and login username:
env.hosts = ['%s@%s' % (USER, HOST)]

# Subdirectory of DJANGO_APP_ROOT in which project sources will be stored
SRC_SUBDIR = 'src'

# Subdirectory of DJANGO_APP_ROOT in which virtualenv will be stored

# Python version
PYTHON_BIN = "python3.4"
PYTHON_PREFIX = ""  # e.g. /usr/local  Use "" for automatic
PYTHON_FULL_PATH = "%s/bin/%s" % (PYTHON_PREFIX, PYTHON_BIN) if PYTHON_PREFIX else PYTHON_BIN

VENV_SUBDIR = 'venv_py34'

WSGI_MODULE = '%s.wsgi' % APP_NAME

THIS_DIR = rel(".")
PARENT_DIR = rel("..")
WEBAPPS_ROOT = '/home/%s/webapps' % USER

USERMEDIA_LOCAL = join(PARENT_DIR, 'usermedia')
USERMEDIA_PRODUCTION = join(WEBAPPS_ROOT, 'cciw_usermedia')

LOCAL_DB_BACKUPS = rel("..", "db_backups")


class Target(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

        # Directory where everything to do with this app will be stored on the server.
        self.DJANGO_APP_ROOT = '/home/%s/webapps/%s_django' % (USER, self.APP_BASE_NAME)
        # Directory where static sources should be collected.  This must equal the value
        # of STATIC_ROOT in the settings.py that is used on the server.
        self.STATIC_ROOT = '/home/%s/webapps/%s_static' % (USER, self.APP_BASE_NAME)

        self.SRC_DIR = join(self.DJANGO_APP_ROOT, SRC_SUBDIR)
        self.VENV_DIR = join(self.DJANGO_APP_ROOT, VENV_SUBDIR)

        self.GUNICORN_PIDFILE = "%s/gunicorn.pid" % self.DJANGO_APP_ROOT
        self.GUNICORN_LOGFILE = "/home/%s/logs/user/gunicorn_%s.log" % (USER, self.APP_BASE_NAME)

        if self.NAME == "PRODUCTION":
            from cciw.settings_production import DATABASES
        elif self.NAME == "STAGING":
            from cciw.settings_staging import DATABASES
        else:
            assert False, "Unknown target %s" % self.NAME

        self.DB = DATABASES['default']


PRODUCTION = Target(
    NAME="PRODUCTION",
    APP_BASE_NAME=APP_NAME,
    APP_PORT=21182,
    GUNICORN_WORKERS=3,
)

STAGING = Target(
    NAME="STAGING",
    APP_BASE_NAME="%s_staging" % APP_NAME,
    APP_PORT=30079,
    GUNICORN_WORKERS=1,
)

target = None


@task
def production():
    global target
    target = PRODUCTION


@task
def staging():
    global target
    target = STAGING


def virtualenv(venv_dir):
    """
    Context manager that establishes a virtualenv to use,
    """
    return settings(venv=venv_dir)


def run_venv(command, **kwargs):
    run("source %s/bin/activate" % env.venv + " && " + command, **kwargs)


@task
def test():
    local("./manage.py test --settings=cciw.settings_tests cciw.cciwmain.tests cciw.bookings.tests cciw.officers.tests", capture=False)


def install_dependencies():
    if getattr(env, 'no_installs', False):
        return
    ensure_virtualenv()
    with virtualenv(target.VENV_DIR):
        with cd(target.SRC_DIR):
            # Use -q (quiet) to stop errors in fabric/io.py
            run_venv("pip install --upgrade -q pip")
            # pycrypto has error installing on WebFaction due to this:
            # https://bugs.launchpad.net/pycrypto/+bug/1294670
            # So we need custom TMPDIR
            run_venv("mkdir ~/tmp || true")
            run_venv("TMPDIR=~/tmp pip install -q -r requirements.txt")


def ensure_virtualenv():
    if exists(target.VENV_DIR):
        return

    with cd(target.DJANGO_APP_ROOT):
        run("virtualenv --no-site-packages --python=%s %s" %
            (PYTHON_BIN, VENV_SUBDIR))
        run("echo %s > %s/lib/%s/site-packages/projectsource.pth" %
            (target.SRC_DIR, VENV_SUBDIR, PYTHON_BIN))


def ensure_src_dir():
    if not exists(target.SRC_DIR):
        run("mkdir -p %s" % target.SRC_DIR)
    with cd(target.SRC_DIR):
        if not exists(join(target.SRC_DIR, '.hg')):
            run("hg init")


@task
def push_rev(rev):
    """
    Use the specified revision for deployment, instead of the current revision.
    """
    env.push_rev = rev


def push_sources():
    """
    Push source code to server.
    """
    ensure_src_dir()
    push_rev = getattr(env, 'push_rev', None)
    if push_rev is None:
        push_rev = local("hg id", capture=True).split(" ")[0].strip().strip("+")

    local("hg push -f ssh://%(user)s@%(host)s/%(path)s || true" %
          dict(host=env.host,
               user=env.user,
               path=target.SRC_DIR,
               ))
    with cd(target.SRC_DIR):
        run("hg update %s" % push_rev)


@task
def webserver_stop():
    """
    Stop the webserver that is running the Django instance
    """
    run("kill $(cat %s)" % target.GUNICORN_PIDFILE)
    run("rm %s" % target.GUNICORN_PIDFILE)


def _webserver_command():
    return ("%(venv_dir)s/bin/gunicorn --log-file=%(logfile)s -b 127.0.0.1:%(port)s -D -w %(workers)s --pid %(pidfile)s %(wsgimodule)s:application" %
            {'venv_dir': target.VENV_DIR,
             'pidfile': target.GUNICORN_PIDFILE,
             'wsgimodule': WSGI_MODULE,
             'port': target.APP_PORT,
             'workers': target.GUNICORN_WORKERS,
             'logfile': target.GUNICORN_LOGFILE,
             }
            )


@task
def webserver_start():
    """
    Starts the webserver that is running the Django instance
    """
    run(_webserver_command())


@task
def webserver_restart():
    """
    Restarts the webserver that is running the Django instance
    """
    try:
        run("kill -HUP $(cat %s)" % target.GUNICORN_PIDFILE)
    except:
        webserver_start()


def _is_webserver_running():
    try:
        pid = int(open(target.GUNICORN_PIDFILE).read().strip())
    except (IOError, OSError):
        return False
    for ps in psutil.process_iter():
        if (ps.pid == pid and
            any('gunicorn' in c for c in ps.cmdline)
                and ps.username == USER):
            return True
    return False


@task
def local_webserver_start():
    """
    Starts the webserver that is running the Django instance, on the local machine
    """
    if not _is_webserver_running():
        local(_webserver_command())


def rsync_dir(local_dir, dest_dir):
    # clean first
    with settings(warn_only=True):
        local("find -L %s -name '*.pyc' | xargs rm || true" % local_dir, capture=True)
    local("rsync -z -r -L --delete --exclude='_build' --exclude='.hg' --exclude='.git' --exclude='.svn' --delete-excluded %s/ cciw@cciw.co.uk:%s" % (local_dir, dest_dir), capture=False)


def build_static():
    with virtualenv(target.VENV_DIR):
        with cd(target.SRC_DIR):
            run_venv("./manage.py collectstatic -v 0 --noinput --clear")

    run("chmod -R ugo+r %s" % target.STATIC_ROOT)


@task
def first_deployment_mode():
    """
    Use before first deployment to switch on fake migrations.
    """
    env.initial_deploy = True


@task
def first_django_17_deploy():
    env.first_django_17_deploy = True


def update_database():
    with virtualenv(target.VENV_DIR):
        with cd(target.SRC_DIR):
            if getattr(env, 'first_django_17_deploy', False):
                # We have to to do '--fake' because for cciwmain, dependencies
                # meant that two migrations got created, so auto-detecting of
                # initial migration won't cover us.
                run_venv("./manage.py migrate --fake --noinput cciwmain")

                # Has multiple initial migrations we have already applied
                run_venv("./manage.py migrate --fake --noinput django_nyt")

                # Has multiple initial migrations we have already applied
                run_venv("./manage.py migrate --fake --noinput ipn")

                # Everything else
                run_venv("./manage.py migrate --noinput")

            elif getattr(env, 'initial_deploy', False):
                run_venv("./manage.py syncdb --all")
                run_venv("./manage.py migrate --fake --noinput")
            else:
                run_venv("./manage.py syncdb --noinput")
                run_venv("./manage.py migrate --noinput")


NON_VCS_SOURCES = [
    "cciw/settings_priv.py",
    "cciw/settings_priv_common.py",
    "cciw/settings_production.py",
    "cciw/settings_staging.py",
]


def _push_non_vcs_sources():
    for s in NON_VCS_SOURCES:
        local("rsync %s cciw@cciw.co.uk:%s/%s" % (s, target.SRC_DIR, s))


def _get_non_vcs_sources():
    for s in NON_VCS_SOURCES:
        local("rsync cciw@cciw.co.uk:%s/%s %s" % (target.SRC_DIR, s, s))

@task
def deploy():
    """
    Deploy project.
    """
    assert target is not None
    if target is PRODUCTION:

        with lcd(THIS_DIR):
            if local("hg st", capture=True).strip() != "":
                x = input("Project dir is not clean, merge to live will fail. Continue anyway? [y/n] ")
                if x != "y":
                    sys.exit()

    push_sources()
    _push_non_vcs_sources()
    install_dependencies()
    update_database()
    build_static()

    with settings(warn_only=True):
        webserver_stop()
    webserver_start()
    _copy_protected_downloads()

    #  Update 'live' branch so that we can switch to it easily if needed.
    if target is PRODUCTION:
        with lcd(THIS_DIR):
            local('hg update -r live && hg merge -r default && hg commit -m "Merged from default" && hg update -r default', capture=False)


def _copy_protected_downloads():
    # We currently don't need this to be separate for staging and production
    rsync_dir(join(PARENT_DIR, "secure_downloads_src"),
              join(WEBAPPS_ROOT, 'cciw_protected_downloads_src'))
    run("chmod -R ugo+r %s" % join(WEBAPPS_ROOT, 'cciw_protected_downloads_src'))


@task
def no_db():
    """
    Call first to skip upgrading DB
    """
    env.no_db = True


@task
def no_installs():
    env.no_installs = True


@task
def quick():
    no_db()
    no_installs()


@task
def upload_usermedia():
    local("rsync -z -r %s/ cciw@cciw.co.uk:%s" % (USERMEDIA_LOCAL, USERMEDIA_PRODUCTION), capture=False)
    run("find %s -type f -exec chmod ugo+r {} ';'" % USERMEDIA_PRODUCTION)


@task
def backup_usermedia():
    local("rsync -z -r  cciw@cciw.co.uk:%s/ %s" % (USERMEDIA_PRODUCTION, USERMEDIA_LOCAL), capture=False)


# TODO:
#  - backup db task. This should be run only in production, and copies
#    files to Amazon S3 service.


def make_django_db_filename(target):
    return "/home/cciw/db-%s.django.%s.sql" % (target.DB['NAME'], datetime.now().strftime("%Y-%m-%d_%H.%M.%S"))


def dump_db(target):
    filename = make_django_db_filename(target)
    run("pg_dump -Fp --clean -U %s -O -o -f %s %s" % (target.DB['USER'], filename, target.DB['NAME']))
    run("gzip %s" % filename)
    return filename + ".gz"


@task
def get_live_db():
    filename = dump_db(PRODUCTION)
    local("mkdir -p %s" % LOCAL_DB_BACKUPS)
    return list(get(filename, local_path=LOCAL_DB_BACKUPS + "/%(basename)s"))[0]


def db_restore_commands(db, filename):
    if filename.endswith(".gz"):
        extract = "gunzip -c |"
    else:
        extract = ""
    return [
        """cat %s | %s psql -U %s %s""" % (filename, extract, db['USER'], db['NAME']),
        """psql -U %s %s -c "UPDATE django_site SET domain='staging.cciw.co.uk';" """ % (db['USER'], db['NAME']),
        """psql -U %s %s -c "UPDATE django_site SET name='staging.cciw.co.uk';" """ % (db['USER'], db['NAME']),
    ]


@task
def local_restore_from_dump(filename):
    from cciw.settings_dev import DATABASES
    db = DATABASES['default']
    for cmd in db_restore_commands(db, filename):
        local(cmd)


@task
def copy_production_db_to_staging():
    filename = dump_db(PRODUCTION)
    # Don't have permission to create databases on cciw.co.uk, so are limited to pg_restore

    for cmd in db_restore_commands(STAGING.DB, filename):
        run(cmd)


@task
def get_and_load_production_db():
    """
    Dump current production Django DB and load into dev environment
    """
    filename = get_live_db()
    local_restore_from_dump(filename)


# ---- ngrok -----

NGROK_1 = "1"
NGROK_2 = "2"


def get_ngrok_version():
    ngrok_version = subprocess.check_output(["ngrok", "version"]).decode('utf-8')
    if ngrok_version.startswith("1."):
        return NGROK_1
    else:
        return NGROK_2  # Assume anything more recent is compatible with version 2


@task
def run_ngrok(port=8000):
    """
    Launch ngrok, and update Site record to match the URL.
    """
    # We don't want to interfere with ngrok input/output/screen use, so we fork
    # using exec. However, we do need to know what is going on in order know the
    # URL, so we spawn another fab task that monitors a log file

    # Check that this works first, so that set_site_from_url doesn't fail silently
    os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'
    import django
    django.setup()

    # Need a logfile
    log_fd, log_filename = tempfile.mkstemp()
    os.close(log_fd)

    # launch fab in separate process in background.
    os.spawnv(os.P_NOWAIT,
              "/bin/sh", ["sh", "-c", "fab ngrok_helper:{0} > /dev/null 2> /dev/null".format(log_filename)])

    # Now launch ngrok, replacing current process
    ngrokpath = _get_path("ngrok")

    if get_ngrok_version() == NGROK_1:
        os.execv(ngrokpath, ["ngrok", "--log=%s" % log_filename, str(port)])
    else:
        os.execv(ngrokpath, ["ngrok", "http", str(port), "--log-level", "debug", "--log", log_filename])


NGROK_LOG_MATCHERS = {
    NGROK_1: {
        'url': "\[client\] Tunnel established at ([^ ]*)",
        'shutdown': "\[controller\] Shutting down",
    },
    NGROK_2: {
        'url': 'msg="decoded response".* URL:([^ ]*)',
        'shutdown': 'msg="all component stopped"',
    }
}


@task
def ngrok_helper(log_filename):
    matchers = NGROK_LOG_MATCHERS[get_ngrok_version()]

    f = open(log_filename, "r")
    while True:
        line = f.readline()
        if line:
            m = re.search(matchers['url'], line.strip())
            if m:
                set_site_from_url(m.groups()[0])
            if re.search(matchers['shutdown'], line):
                break
        else:
            time.sleep(0.5)
    os.unlink(log_filename)


def _get_path(program_name):
    return subprocess.check_output(["which", program_name]).strip()


@task
def set_site_from_url(url):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'
    import django
    django.setup()
    from django.contrib.sites.models import Site
    from urllib.parse import urlparse
    parts = urlparse(url)
    Site.objects.all().update(domain=parts.netloc)


@task
def initial_dev_setup():
    get_and_load_production_db()
    production()
    _get_non_vcs_sources()
