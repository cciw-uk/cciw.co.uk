from datetime import datetime
from fabric.api import run, local, abort, env, put
from fabric.decorators import hosts, runs_once
from fabric.context_managers import cd, settings
import os

env.hosts = ["cciw@cciw.co.uk"]


# These names apply for the both the apps and the databases on the remote
# server.
STAGING = "cciw_staging"
PRODUCTION = "cciw"

this_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(this_dir)


@runs_once
def ensure_dependencies():
    hg_branch = local("cd deps/django; hg branch")
    if hg_branch.strip() != 'default':
        abort("Django src on incorrect branch")


def test():
    ensure_dependencies()
    local("cd project; ./manage.py test cciwmain officers tagging utils --settings=cciw.settings_tests", capture=False)


def _prepare_deploy():
    #test()
    ensure_dependencies()
    # test that we can do forwards and backwards migrations?
    # check that there are no outstanding changes.


@hosts("cciw@cciw.co.uk")
def backup_database(dbname, label):
    fname = "%s-%s.db" % (dbname, label)
    run("dump_cciw_db.sh %s %s" % (dbname, fname))


def virtualenv(command):
    run(env.venv + " && " + command)


def _update_symlink(dest_dir):
    with cd(dest_dir + "/../"):
        run("rm current")
        run("ln -s %s current" % os.path.basename(dest_dir))


def _fix_ipython():
    # Fix up IPython, which gets borked by the re-installation of the virtualenv
    with settings(warn_only=True):
        virtualenv("pip uninstall -y ipython")
        virtualenv("pip install ipython")


def _update_virtualenv(dest_dir, all_deps):
    # Update virtualenv in new dir.
    with cd(dest_dir):
        # We should already have a virtualenv, but it will need paths updating
        run("virtualenv --python=python2.5 env")
        with settings(venv="source %s/env/bin/activate" % dest_dir):
            with cd("project"):
                virtualenv("pip install -r requirements.txt")
            _fix_ipython()

        # Need to add project and deps to path.
        # Could do 'python setup.py develop' but not all projects support it
        pth_file = '\n'.join("../../../../" + n for n in all_deps)
        pth_name = "deps.pth"
        with open(pth_name, "w") as fd:
            fd.write(pth_file)
        put(pth_name, dest_dir + "/env/lib/python2.5/site-packages")
        os.unlink(pth_name)


def _stop_apache(target):
    run ("/home/cciw/webapps/" + target + "/apache2/bin/stop")


def _start_apache(target):
    run ("/home/cciw/webapps/" + target + "/apache2/bin/start")


def _restart_apache(target):
    with settings(warn_only=True):
        _stop_apache(target)
    _start_apache(target)


def rsync_dir(local_dir, dest_dir):
    # clean first
    with settings(warn_only=True):
        local("find %s -name '*.pyc' -exec 'rm {}' ';'" % local_dir)
    local("rsync -r -L --delete --exclude='_build' --exclude='.hg' --exclude='.git' --exclude='.svn' --delete-excluded %s cciw@cciw.co.uk:%s/" % (local_dir, dest_dir))

def _copy_local_sources(dest_dir, deps, project_dir):
    # Upload local sources. For speed, we:
    # - make a copy of the sources that are there already, if they exist.
    # - rsync to the copies.
    # This also copies the virtualenv which is contained in the same folder,
    # which saves a lot of time with installing.
    current_srcs = os.path.dirname(dest_dir) + "/current"
    run("cp -a -L %s %s" % (current_srcs, dest_dir))

    with cd(parent_dir):
        # rsync the project.
        rsync_dir(project_dir, dest_dir)

        # rsync dependencies.
        # These are the dependencies which may have been patched locally and so
        # are not in the requirements.txt file.
        for depname in deps:
            with cd("deps/"):
                rsync_dir(depname, dest_dir)


def _deploy(target):
    label = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    _prepare_deploy()
    db_backup_name = backup_database(target, label)

    dest_dirname = "src-%s" % label
    dest_dir =  "/home/cciw/webapps/" + target + "/src/" + dest_dirname

    project_dir = 'project'
    deps = ['django', 'django-mailer']
    all_deps = deps + [project_dir]

    _copy_local_sources(dest_dir, deps, project_dir)
    _update_virtualenv(dest_dir, all_deps)


    # TODO
    # - stop apache instance (OK if not running)
    # - user media
    # - rsync protected_downloads dir
    # - do db migrations
    # - if unsuccessful
    #    - rollback db migrations
    #      - if unsuccessful, restore from db_backup_name
    # - if successful
    #    - remove 'current' symlink (OK if not present)
    #    - add new current symlink to '$datetime' dir
    #  - start apache


    _update_symlink(dest_dir)
    _restart_apache(target)




def deploy_staging():
    _deploy(STAGING)


def deploy_production():
    return # not ready yet
    _deploy(PRODUCTION)
