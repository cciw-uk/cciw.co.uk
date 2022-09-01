# Utilities needed by factories
import itertools
from typing import Any, Callable, Generator, TypeVar


class FactoriesBase:
    _all_factory_instances = []

    def __new__(cls):
        instance = super().__new__(cls)
        FactoriesBase._all_factory_instances.append(instance)
        return instance

    @staticmethod
    def clear_instances():
        # Model factories cache created instances, which is problematic
        # when the object is re-used for the next test, but the record
        # doesn't exist in the database.

        # We cannot easily delete factory instances, because there are
        # references to them in other modules. But we can reset them to a
        # pristine condition, by creating a new instance and assigning __dict__

        # Avoid infinite loop by making a copy of _all_factory_instances
        instances = FactoriesBase._all_factory_instances[:]
        for instance in instances:
            instance.__dict__ = instance.__class__().__dict__
        # Discard the new instances we just created above
        FactoriesBase._all_factory_instances = instances

        # We also want to clear @lru_cache() on all methods
        for subclass in FactoriesBase.__subclasses__():
            for k, val in subclass.__dict__.items():
                if hasattr(val, "cache_clear"):
                    val.cache_clear()


class _Auto:
    """
    Sentinel value used when 'None' would be allowed due to a nullable database field.
    """

    def __bool__(self):
        return False


Auto: Any = _Auto()

T = TypeVar("T")


def sequence(func: Callable[[int], T]) -> Generator[T, None, None]:
    """
    Generates a sequence of values from the passed in lambda that takes an integer,
    and a sequence of integers started at zero.
    """
    return (func(n) for n in itertools.count())
