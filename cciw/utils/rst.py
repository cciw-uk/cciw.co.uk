import docutils.core
from django.utils.encoding import force_str, smart_str
from django.utils.safestring import mark_safe
from docutils.writers import html4css1


def rst_to_html(text: str, initial_header_level=1):
    settings = RST_SETTINGS | {"initial_header_level": initial_header_level}
    parts = docutils.core.publish_parts(
        source=smart_str(text), settings_overrides=settings, writer=TextutilsHTMLWriter()
    )
    return mark_safe(force_str(parts["body"]))


RST_SETTINGS = {
    "initial_header_level": 1,
    "doctitle_xform": False,
    "language_code": "en",
    "footnote_references": "superscript",
    "trim_footnote_reference_space": True,
    "default_reference_context": "view",
    "link_base": "",
    "raw_enabled": False,
    "file_insertion_enabled": False,
    "embed_stylesheet": False,
    "stylesheet": None,
}


class TextutilsHTMLWriter(html4css1.Writer):
    def __init__(self):
        html4css1.Writer.__init__(self)
        self.translator_class = TextutilsHTMLTranslator


class TextutilsHTMLTranslator(html4css1.HTMLTranslator):
    def __init__(self, document):
        html4css1.HTMLTranslator.__init__(self, document)

    def visit_admonition(self, node, name=""):
        self.body.append(self.starttag(node, "div", CLASS=(name or "admonition")))
        self.set_first_last(node)

    def visit_footnote(self, node):
        self.body.append(self.starttag(node, "p", CLASS="footnote"))
        self.footnote_backrefs(node)

    def depart_footnote(self, node):
        self.body.append("</p>\n")

    def visit_label(self, node):
        self.body.append(self.starttag(node, "strong", f"[{self.context.pop()}", CLASS="label"))

    def depart_label(self, node):
        self.body.append(f"</a>]</strong> {self.context.pop()}")
