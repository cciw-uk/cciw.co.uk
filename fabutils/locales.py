from fabric.connection import Connection


def install(c: Connection, project_locale):
    locale = project_locale.replace("UTF-8", "utf8")
    if locale not in c.run("locale -a", hide=True).stdout:
        c.run(f"locale-gen {project_locale}", echo=True)
        c.run(f"update-locale {project_locale}", echo=True)
