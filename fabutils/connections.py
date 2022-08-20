from contextlib import contextmanager
from typing import Any, Callable, TypeVar, cast

from fabric import task as fabtask
from fabric.connection import Connection
from invoke import task as invoke_task
from invoke.config import Config
from invoke.context import Context
from makefun import wraps

# -- Generic connection utilities  ---

# Constraints:
# - app user doesn't have sudo rights on server, for tighter security.
#   This means we can't use a single connection and 'sudo'
# - so we do root tasks using separate root user login connection,
#   only where necessary.
# - we want to call both root tasks and normal tasks directly at
#   the top level
# - we want to call root tasks from normal tasks, and via versa.
# - we want to be able to support passing `--hosts` from CLI
#   (this is typically only done when migrating from one host to another)
# - thankfully, we don't need to support multiple hosts.

# So we define `task` and `root_task` decorators to manage this.


@contextmanager
def set_connection_user(connection: Connection, new_user: str) -> Connection:
    """
    Context manager to change the connection to the specified user,
    creating a new connection if needed.
    """
    if connection.user == new_user:
        yield connection
    else:
        new_connection = get_or_create_connection(connection.host, connection.port, new_user, connection.config)
        yield new_connection
        # Stash after first use, so that it will be active
        # when we next come to use it.
        stash_connection(new_connection)


_CACHED_CONNECTIONS: dict[tuple[str, int, str], Connection] = {}


def get_or_create_connection(host: str, port: int, user: str, config: Config):
    """
    Get a connection matching user@host:port and the config, or create
    a new one
    """
    # Config is not hashable, so we can't put it in dict, but we can compare
    # for object equality. So for the common case of not changing config, we
    # can re-use already opened connections.

    cached = _CACHED_CONNECTIONS.get((host, port, user), None)
    if cached is not None and cached.config == config:
        return cached
    return Connection(host=host, port=port, user=user, config=config)


def stash_connection(connection: Connection):
    if connection.is_connected:
        _CACHED_CONNECTIONS[connection.host, connection.port, connection.user] = connection


F = TypeVar("F", bound=Callable[..., Any])


def managed_connection_task(user: str, host: str) -> Callable[..., Callable[[F], F]]:
    """
    Returns a decorator (generator) that is like `@task()` from
    from fabric, but handles connections so that:
    - the host is the specified host by default
    - the task is passed a connection opened with the specified username

    Normally used like:

      myuser_task = managed_connection_task("myuser", "myhost")

      @myuser_task(...)
      def hello(c):
          c.run("echo hello")

    """

    def _generator(*task_args, **task_kwargs) -> Callable[[F], F]:

        # Set the "hosts" string so that top-level calling of the task works
        # (unless `hosts=` was specified at task level)
        if "hosts" not in task_kwargs:
            task_kwargs["hosts"] = [f"{user}@{host}"]

        def _decorator(task_func: F) -> F:
            @wraps(task_func)
            def _wrapper(c, *args, **kwargs):
                # Inside the function, we have to swap out the connection if we
                # get one with the wrong user. This occurs when the task is called
                # from another.
                with set_connection_user(c, user) as new_c:
                    retval = task_func(new_c, *args, **kwargs)
                return retval

            return cast(F, fabtask(*task_args, **task_kwargs)(_wrapper))

        return _decorator

    return _generator


def local_task(*task_args, **task_kwargs):
    """
    Decorator that ensure a task is run only as a local task,
    never using remote connections.
    """

    def decorator(func):
        @invoke_task(*task_args, **task_kwargs)
        @wraps(func)
        def wrapper(c, *args, **kwargs):
            if isinstance(c, Connection):
                # Replace fabric's Connection with Invoke Context.
                # We perhaps need something better here to respect any other config?
                context = Context()
            else:
                context = c
            return func(context, *args, **kwargs)

        return wrapper

    return decorator
