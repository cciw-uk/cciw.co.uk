from pathlib import Path
from unittest.mock import Mock

from pyastgrep.api import Match, process_python_file_cached, search_python_files

from cciw.utils.functional import partition

SRC_ROOT = Path(__file__).parent.parent.parent.resolve()


def assert_expected_pyastgrep_matches(xpath_expr: str, *, expected_count: int, message: str):
    """
    Asserts that the pyastgrep XPath expression matches only `expected_count` times,
    each of which must be marked with `pyastgrep_exception`

    `message` is a message to be printed on failure.

    """
    xpath_expr = xpath_expr.strip()
    matches: list[Match] = [
        item
        for item in search_python_files([SRC_ROOT], xpath_expr, python_file_processor=process_python_file_cached)
        if isinstance(item, Match)
    ]

    expected_matches, other_matches = partition(matches, key=lambda match: "pyastgrep: expected" in match.matching_line)

    if len(expected_matches) < expected_count:
        assert False, f"Expected {expected_count} matches but found {len(expected_matches)} for {xpath_expr}"

    assert not other_matches, (
        message
        + "\n Failing examples:\n"
        + "\n".join(
            f"  {match.path}:{match.position.lineno}:{match.position.col_offset}:{match.matching_line}"
            for match in other_matches
        )
    )


def test_inclusion_tag_names():
    """
    Check that all @inclusion_tag usages have a function name matching the file name.
    """

    assert_expected_pyastgrep_matches(
        """
          //FunctionDef[
            decorator_list/Call/func/Attribute[@attr="inclusion_tag"] and not(
              contains(decorator_list/Call/args/Constant/@value,
                       concat("/", @name, ".html")) or
              contains(decorator_list/Call/keywords/keyword[@arg="filename"]/value/Constant/@value,
                       concat("/", @name, ".html"))
              )
          ]
          """,
        message="The @inclusion_tag function name should match the template file name",
        expected_count=3,
    )


# Examples of what test_inclusion_tag_names is looking for:

register = Mock()


@register.inclusion_tag(filename="something/not_bad.html", takes_context=True)
def bad(context):  # pyastgrep: expected
    pass


@register.inclusion_tag(filename="something/not_bad2.html")
def bad2():  # pyastgrep: expected
    pass


# positional arg
@register.inclusion_tag("something/not_bad3.html")
def bad3():  # pyastgrep: expected
    pass


# Good examples that don't need `pyastgrep: expected`, for debugging:


@register.inclusion_tag(filename="something/good.html")
def good():
    pass


@register.inclusion_tag("something/good2.html")
def good2():
    pass


def test_boolean_arguments_are_keyword_only():
    """
    Check that any function arguments with type hint of `bool` should be keyword argument only.

    This is because in calls like `do_thing(123, True)`, the `True` argument is almost always
    difficult to decipher, while `do_thing(123, dry_run=True)` is much better.
    """
    assert_expected_pyastgrep_matches(
        """
        .//FunctionDef/args/arguments/args/arg/annotation/Name[@id="bool"]
        """,
        message="Function arguments with type `bool` should be keyword-only",
        expected_count=3,
    )


# Examples:


def good_boolean_arg(*, foo: bool):
    pass


def good_boolean_arg_2(*, foo: bool = True):
    pass


def good_boolean_arg_3(*, x: int, foo: bool = True):
    pass


def good_boolean_arg_4(x: int, *, foo: bool = True):
    pass


def bad_boolean_arg(foo: bool):  # pyastgrep: expected
    pass


def bad_boolean_arg_2(foo: bool = True):  # pyastgrep: expected
    pass


def bad_boolean_arg_3(x: int, foo: bool = True):  # pyastgrep: expected
    pass
