# Utilities needed by factories
import itertools
from collections.abc import Callable, Generator
from typing import Any, TypeVar


class _Auto:
    """
    Sentinel value used when 'None' would be allowed due to a nullable database field.
    """

    def __bool__(self):
        # Allow `Auto` to be used like `None` or `False` in boolean expressions
        return False


Auto: Any = _Auto()

T = TypeVar("T")


def sequence(func: Callable[[int], T]) -> Generator[T, None, None]:
    """
    Generates a sequence of values from a sequence of integers starting at zero,
    passed through the callable, which must take an integer argument.
    """
    return (func(n) for n in itertools.count())
