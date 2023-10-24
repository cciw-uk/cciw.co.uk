"""
"Literate YAML"

A subset of YAML designed for nicely formatted, human readable documents
that are also machine readable.

This module provides functionality for formatting them.
"""

from collections.abc import Generator, Iterable
from dataclasses import dataclass

# Current strategy:
#
# - For marked up text, we support only "top level" comments i.e. comments with
#   `#` in the first column. Everything else is treated as a normal YAML comment.
# - pre-parse the YAML, converting into sequence of text blocks and YAML blocks.
# - assume the text is rst, and make a large rst document containing the YAML
#   as code blocks.
# - render rst to HTML
#
# This has many limitations, but works for our needs.

# Alternative strategies we considered:
#
# ruamel 1:
#   - Use the ruamel parser, which preserves comments
#   - then go through "top level" comments and pull them out as rst markup items
#   - and remaining YAML turn into rst `.. code-block:: YAML` interspersed between RST blocks
#
#   It was discovered, however, that the nodes ruamel attaches comments to are
#   often very unhelpful e.g. what look like "top level" comments in between
#   two list items are attached to the last child node of the first list item.
#
#   This means the parsed structure is very inconvenient for re-interpreting
#   as blocks of text markup between YAML items.
#
# ruamel 2:
#   - Parse using ruamel
#   - Iterate over CST, pulling out and replacing comment codes with some marker
#     like `commentid-123456`
#   - Render YAML using something like pygments
#   - Post process the HTML, replacing `commentid-123456` etc with formatted text blocks


@dataclass
class RstBlock:
    text: str

    def as_rst(self):
        return self.text


@dataclass
class YamlBlock:
    text: str

    def as_rst(self):
        return ".. code-block:: yaml\n\n" + "\n".join("   " + line for line in self.text.strip().split("\n")) + "\n"


def literate_yaml_to_rst(yaml_source):
    blocks = parse_literate_yaml(yaml_source)
    return "\n".join(block.as_rst() for block in blocks)


def parse_literate_yaml(yaml_source: str) -> list[RstBlock | YamlBlock]:
    return list(_merge_blocks(_extract_blocks(yaml_source)))


def _merge_blocks(blocks: Iterable[RstBlock | YamlBlock]) -> Generator[RstBlock | YamlBlock, None, None]:
    growing_block = None

    def yield_growing():
        if growing_block is not None and growing_block.text.strip():
            growing_block.text += "\n"
            yield growing_block

    for block in blocks:
        if growing_block is not None and type(growing_block) == type(block):
            growing_block.text += "\n" + block.text
        else:
            yield from yield_growing()
            growing_block = block
    yield from yield_growing()


def _extract_blocks(yaml_doc: str) -> Generator[RstBlock | YamlBlock, None, None]:
    for line in yaml_doc.split("\n"):
        if line.startswith("# "):
            yield RstBlock(line[2:])
        elif line == "#":
            yield RstBlock("")
        else:
            yield YamlBlock(line)
