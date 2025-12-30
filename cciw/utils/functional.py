from collections.abc import Callable, Iterable


def partition[T](values: Iterable[T], key: Callable[[T], bool]) -> tuple[list[T], list[T]]:
    """
    Partition a list into truthy/falsey values, as determined by `key` function
    """
    truthy: list[T] = []
    falsey: list[T] = []
    for item in values:
        if key(item):
            truthy.append(item)
        else:
            falsey.append(item)
    return (truthy, falsey)
