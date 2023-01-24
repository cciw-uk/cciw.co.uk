from cciw.utils.literate_yaml import RstBlock, YamlBlock, literate_yaml_to_rst, parse_literate_yaml


def test_merge_blocks():
    src = """
# Comment 1
#
# Comment 2
- field: value
  field2: value
- item
# Comment 3
"""
    assert parse_literate_yaml(src) == [
        RstBlock("Comment 1\n\nComment 2\n"),
        YamlBlock("- field: value\n  field2: value\n- item\n"),
        RstBlock("Comment 3\n"),
    ]


def test_literate_yaml_to_rst():
    src = """
# Comment
- item
- item2
# Comment
""".lstrip()

    assert (
        literate_yaml_to_rst(src)
        == """
Comment

.. code-block:: yaml

   - item
   - item2

Comment
""".lstrip()
    )
