#!/usr/bin/env python

# Ham-fisted approach to squashing migrations, to avoid including data
# migrations, and various Django bugs with migration squashing.

from __future__ import absolute_import, print_function, unicode_literals

import glob
import importlib
import os
import subprocess
from datetime import datetime

os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'
import django  # NOQA isort:skip

django.setup()

from django.conf import settings  # NOQA isort:skip


PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))


def main():
    app_migration_modules = get_migration_modules_to_reset()
    old_app_migrations = get_existing_migration_files_for_apps(app_migration_modules)

    # Hide migrations so that Django thinks there are no migrations.
    hidden_migrations = hide_existing_migrations(app_migration_modules, old_app_migrations)

    # Make new ones from scatch, with no data migrations
    make_new_migrations(app_migration_modules)

    # Rename new ones to avoid clashes
    new_app_migrations = get_existing_migration_files_for_apps(app_migration_modules)
    migration_name_changes = rename_migrations(app_migration_modules, new_app_migrations)

    # Refresh because we just renamed files
    new_app_migrations = get_existing_migration_files_for_apps(app_migration_modules)

    # Rewrite migrations to respect renames and add 'replaces'
    # to make them squashed migrations.
    rewrite_new_migrations(app_migration_modules, new_app_migrations,
                           old_app_migrations, migration_name_changes)

    # Restore hidden migrations
    unhide_hidden_migrations(hidden_migrations)


def get_migration_modules_to_reset():
    apps = get_thisproject_apps()
    app_migrations = {}
    for app in apps:
        migration_mod = settings.MIGRATION_MODULES.get(app,
                                                       app + ".migrations")
        p = path_for_migration_mod(migration_mod)
        if not os.path.isdir(p):
            continue
        app_migrations[app] = migration_mod

    for app, migration_mod in settings.MIGRATION_MODULES.items():
        if app in app_migrations:
            continue

        mod = importlib.import_module(migration_mod)
        if mod.__file__.startswith(PROJECT_PATH):
            # An app whose migrations we are overriding
            app_migrations[app] = migration_mod

    return app_migrations


def get_thisproject_apps():
    retval = []
    for app in settings.INSTALLED_APPS:
        try:
            app_name = app
            mod = importlib.import_module(app_name)
        except ImportError:
            mod_name, obj_name = app.rsplit('.', 1)
            mod = importlib.import_module(mod_name)
            app_name = getattr(mod, obj_name).name

        if mod.__file__.startswith(PROJECT_PATH):
            retval.append(app_name)
    return retval


def path_for_migration_mod(mod_name):
    return os.path.join(PROJECT_PATH, mod_name.replace('.', '/'))


def get_existing_migration_files_for_apps(app_migration_modules):
    app_migrations = {}

    for app, migration_mod in app_migration_modules.items():
        p = path_for_migration_mod(migration_mod)
        migrations = sorted([
            f for f in os.listdir(p)
            if f.endswith(".py") and not f == '__init__.py'])
        app_migrations[app] = migrations

    assert sorted(app_migration_modules.keys()) == sorted(app_migrations.keys())
    return app_migrations


def hide_existing_migrations(app_migration_modules, old_app_migrations):

    hidden = []

    # Hide existing migrations
    for app, migrations in old_app_migrations.items():
        migration_mod_path = path_for_migration_mod(app_migration_modules[app])

        for migration in migrations:
            f = os.path.join(migration_mod_path, migration)
            print("Hiding: " + f)
            f_hidden = f + ".hidden"
            os.rename(f, f_hidden)
            hidden.append((f, f_hidden))
        for f in glob.glob(os.path.join(migration_mod_path, '*.pyc')):
            os.unlink(f)

    return hidden


def make_new_migrations(app_migration_modules):
    app_names = [app.rsplit('.')[-1] for app in app_migration_modules.keys()]
    subprocess.check_call(["./manage.py", "makemigrations"] + app_names)


def rename_migrations(app_migration_modules, new_app_migrations):

    # Many need to be renamed to avoid clashes with the hidden migrations
    new_name_stem = "squashed_{0}".format(datetime.now().strftime("%Y%m%d"))

    migration_name_changes = {}
    for app, migration_mod in app_migration_modules.items():
        migration_mod_path = path_for_migration_mod(migration_mod)

        for filename in new_app_migrations[app]:
            f_start, f_end = filename.split('_', 1)
            new_filename = "{0}_{1}_{2}".format(f_start, new_name_stem, f_end)
            old_migration_name = filename.replace(".py", "")
            new_migration_name = new_filename.replace(".py", "")
            migration_name_changes[(app, old_migration_name)] = (app, new_migration_name)
            os.rename(os.path.join(migration_mod_path, filename),
                      os.path.join(migration_mod_path, new_filename))

    return migration_name_changes


def rewrite_new_migrations(app_migration_modules, new_app_migrations,
                           old_app_migrations, migration_name_changes):

    # Mostly there will be '0001_initial' migrations, but there will also be
    # 0002_* due to cyclic dependencies. Both types need to be marked as
    # squashed migrations, because we don't want them to run on existing
    # installs.

    # All need to have dependencies rewritten (due to renames),
    # and all need a 'replaces' lines added.

    for app, migration_mod in app_migration_modules.items():
        migration_mod_path = path_for_migration_mod(migration_mod)

        new_migration_files = new_app_migrations[app]

        app_name = app.split('.')[-1]
        available_replaces = [(app_name,
                               f.replace('.py', ''))
                              for f in old_app_migrations[app]]

        # If new_migration_files has more than one item, we need to split up
        # available_replaces between them.
        taken = 0
        replaces_for_file = {}
        for i, m_file in enumerate(new_migration_files):
            num_to_leave = len(new_migration_files) - (i + 1)
            stop = -num_to_leave if num_to_leave > 0 else None
            replaces_to_take = available_replaces[taken:stop]
            taken += len(replaces_to_take)
            replaces_for_file[m_file] = replaces_to_take

        for m_file in new_migration_files:
            full_file_name = os.path.join(migration_mod_path, m_file)
            contents = open(full_file_name, "rb").read()

            # Now fix to make it actually a squashed migration
            replaces = replaces_for_file[m_file]
            replaces_line = b'\n    replaces = %r\n' % replaces

            # Add replaces:
            needle = b'class Migration(migrations.Migration):\n'
            new_contents = contents.replace(needle, needle + replaces_line)

            # We also need to fix any dependencies
            # that have '0001_initial' to '0001_squashed_initial'.
            new_contents = fix_renamed_dependencies(new_contents, migration_name_changes)

            with open(full_file_name, "wb") as f:
                f.write(new_contents)


def fix_renamed_dependencies(migration_contents, migration_name_changes):
    # Quick and dirty, string based
    out = []
    for line in migration_contents.split(b"\n"):
        for (from_app, from_name), (to_app, to_name) in migration_name_changes.items():
            from_app_name = from_app.split('.')[-1]
            to_app_name = to_app.split('.')[-1]
            needle = "('{0}', '{1}'),".format(from_app_name, from_name).encode('utf-8')
            replacement = "('{0}', '{1}'),".format(to_app_name, to_name).encode('utf-8')
            if line.endswith(needle):
                line = line[0:-len(needle)] + replacement
        out.append(line)
    return b"\n".join(out)


def unhide_hidden_migrations(hidden_migrations):
    # Unhide the hidden migrations
    for f, f_hidden in hidden_migrations:
        if os.path.exists(f):
            raise Exception("File {0} unexpectedly present".format(f))
        os.rename(f_hidden, f)


if __name__ == '__main__':
    main()
