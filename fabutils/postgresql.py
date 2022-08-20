from dataclasses import dataclass
from shlex import quote
from typing import Protocol

from fabric.connection import Connection
from invoke.runners import Result

# -- Database utilities


@dataclass
class Database:
    name: str
    user: str
    password: str
    port: str
    locale: str


class DbCommand(Protocol):
    def execute(self, c: Connection) -> Result:
        pass


@dataclass
class PsqlCommand:
    sql: str
    db: Database
    run_as_postgres: bool = False
    return_tuples: bool = False

    def execute(self, c: Connection, hide: str | None = "stdout") -> Result:
        with c.cd("/"):  # avoid "could not change directory" warnings
            user = "postgres" if self.run_as_postgres else self.db.user
            db_name = "postgres" if self.run_as_postgres else self.db.name
            extra_args = "-t" if self.return_tuples else ""
            cmd = f"psql -p {self.db.port} -U {user} -d {db_name} {extra_args} -c {quote(self.sql)}"
            pg_env = db_to_pg_envs(self.db)
            if self.run_as_postgres:
                cmd = f"sudo -u postgres {cmd}"
                pg_env.pop("PGUSER")
                pg_env.pop("PGPASSWORD")
            return c.run(cmd, echo=True, hide=hide, env=pg_env)


PG_ENVIRON_MAP = {
    "name": "PGDATABASE",
    "port": "PGPORT",
    "user": "PGUSER",
    "password": "PGPASSWORD",
    # Not in Database class:
    #   "host": "PGHOST",
}


def db_to_pg_envs(db: Database) -> dict:
    """
    Returns the environment variables that postgres CLI tools like psql
    and pg_dump use, as a dict.
    """
    return {env_name: getattr(db, attr_name) for attr_name, env_name in PG_ENVIRON_MAP.items()}


@dataclass
class DbCommandGroup:
    commands: list[DbCommand]

    def execute(self, c: Connection) -> Result:
        for command in self.commands:
            command.execute(c)


# DB commands


def sql_quote(sql: str):
    return sql.replace("'", "''")


def create_db_command(db: Database) -> DbCommand:
    return DbCommandGroup(
        [
            # CREATE DATABASE command has to be in separate call, otherwise get
            #   "CREATE DATABASE cannot run inside a transaction block"
            PsqlCommand(
                sql=(
                    f"CREATE DATABASE {db.name} "
                    f"  TEMPLATE = template0 ENCODING = 'UTF8' LC_CTYPE = '{db.locale}' LC_COLLATE = '{db.locale}';"
                ),
                db=db,
                run_as_postgres=True,
            ),
            PsqlCommand(
                sql=(f"GRANT ALL ON DATABASE {db.name} TO {db.user};" f"ALTER USER {db.user} CREATEDB;"),
                db=db,
                run_as_postgres=True,
            ),
        ]
    )


def create_db(c: Connection, db: Database) -> Result:
    return create_db_command(db).execute(c)


def drop_db_if_exists_command(db: Database) -> DbCommand:
    return PsqlCommand(
        sql=f"DROP DATABASE IF EXISTS {db.name};",
        db=db,
        run_as_postgres=True,
    )


def drop_db_if_exists(c: Connection, db: Database) -> Result:
    return drop_db_if_exists_command(db).execute(c)


@dataclass
class PGRestore:
    db: Database
    filename: str
    clean: bool = False

    def execute(self, c: Connection) -> Result:
        with c.cd("/"):
            db = self.db
            cmd = f"pg_restore -h localhost -O -U {db.user} {' -c ' if self.clean else ''} -d {db.name} {quote(self.filename)}"
            return c.run(cmd, echo=True)


def restore_db_command(db: Database, filename: str) -> DbCommand:
    return PGRestore(db, filename)


def restore_db(c: Connection, db: Database, filename: str) -> Result:
    return restore_db_command(db, filename).execute(c)


def create_user_command(db: Database, username: str, password: str) -> DbCommand:
    return PsqlCommand(
        f"CREATE USER {sql_quote(username)} WITH PASSWORD '{sql_quote(password)}';",
        db=db,
        run_as_postgres=True,
    )


def create_user(c: Connection, db: Database, username: str, password: str) -> Result:
    return create_user_command(db, username, password).execute(c)


def create_default_user(c: Connection, db: Database) -> Result:
    return create_user(c, db, db.user, db.password)


def check_user_exists_command(db: Database, username: str) -> DbCommand:
    return PsqlCommand(
        f"""SELECT COUNT(*) FROM pg_user WHERE usename='{sql_quote(username)}'; """,
        db,
        # Normally, doesn't technically require postgres user.
        # But we run command when there might not be any other
        # user or DB existing.
        run_as_postgres=True,
        return_tuples=True,
    )


def check_user_exists(c: Connection, db: Database, username: str) -> bool:
    return check_user_exists_command(db, username).execute(c).stdout.strip() == "1"


def check_database_exists_command(db: Database) -> DbCommand:
    return PsqlCommand(
        f"""SELECT COUNT(*) FROM pg_database WHERE datname='{sql_quote(db.name)}'; """,
        db,
        # Normally, doesn't technically require postgres user.
        # But we run command when there might not be any other
        # user or DB existing.
        run_as_postgres=True,
        return_tuples=True,
    )


def check_database_exists(c: Connection, db: Database) -> bool:
    return check_database_exists_command(db).execute(c).stdout.strip() == "1"
