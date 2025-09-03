"""
Utilities for locust loadtests
"""

from __future__ import annotations

import urllib.parse
from functools import cached_property

import requests
from bs4 import BeautifulSoup
from lxml.html import HtmlElement
from pyquery import PyQuery
from requests import Response

from cciw.utils.loadtests.forms import Checkbox, Form

# This is mostly based on django-functest and WebTest, there are probably lots
# of bugs and things that could be cleaned up.


# Developing this:
#
# - running locust will make things difficult to debug
# - so instead, use something like the `create_page()` function
#   then test interactively


def create_page() -> Page:
    client = requests.Session()
    client.verify = False
    page = Page(client=client)
    return page


class Page:
    """
    Utilities to make it easier to script user behaviour with browser-like interactions
    """

    # At run-time, for intended usage we'll actually have a
    # session object from locust.clients.HttpSession.
    # For testing, we support `requests.Session`

    def __init__(self, client: requests.Session) -> None:
        self.client = client
        self.last_response: PageResponse | None = None
        self.last_url: str | None = None
        # TODO - submit() etc.
        self.last_form: Form | None = None

    def client_get(self, *args, **kwargs) -> requests.Response:
        self._add_referer(kwargs)
        return self.client.get(*args, **kwargs)

    def client_post(self, *args, **kwargs) -> requests.Response:
        self._add_referer(kwargs)
        return self.client.post(*args, **kwargs)

    def _add_referer(self, kwargs: dict) -> None:
        if self.last_url:
            headers = kwargs.get("headers", {})
            headers["referer"] = self.last_url
            kwargs["headers"] = headers

    def _set_response(self, response: Response):
        response.raise_for_status()
        self.last_url = response.request.url
        self.last_response = PageResponse(response)

    def go(self, url: str):
        self._set_response(self.client_get(url))

    def follow_link(self, css_selector=None, text=None):
        """
        Follows the link specified by CSS in css_selector= or matching the text in text=
        """
        assert self.last_response is not None
        assert self.last_url is not None
        if css_selector is not None and text is not None:
            raise ValueError("pass only one of text= or css_selector= to follow_link")
        elif css_selector is not None:
            elems = self.last_response.pq.find(css_selector)
            if len(elems) == 0:
                raise WebTestNoSuchElementException(f"Can't find element matching '{css_selector}'")
        elif text is not None:
            # cssselect (via PyQuery) handles the implementation of :contains()
            # and doesn't do any escaping, so we escape here
            escaped_text = text.replace('"', '\\"')
            css_expr = f'a:contains("{escaped_text}")'

            elems = self.last_response.pq.find(css_expr)

            if len(elems) == 0:
                raise WebTestNoSuchElementException(f"Can't find a link with the text '{text}'")
        else:
            raise ValueError("follow_link requires either a text= or css_selector= argument")

        hrefs = []
        for e in elems:
            if "href" in e.attrib:
                hrefs.append(e.attrib["href"])

        if not hrefs:
            raise WebTestCantUseElement(f"No href attribute found for '{css_selector}'")

        if not all(h == hrefs[0] for h in hrefs):
            raise WebTestMultipleElementsException(
                f"Different href values for links '{css_selector}': '{' ,'.join(hrefs)}'"
            )
        final_url = urllib.parse.urljoin(self.last_url, hrefs[0])
        self.go(final_url)

    def fill(self, data: dict[str, str]):
        """
        Fills form inputs using the values in fields, which is a dictionary
        of CSS selectors to values.
        """
        assert self.last_response is not None
        for selector, value in data.items():
            form, field_name, elem = self._find_form_and_field_by_css_selector(self.last_response, selector)
            field_items = form.fields[field_name]
            if isinstance(field_items, list) and len(field_items) > 1:
                # We've got something like a set of checkboxes with the same name.
                selected_value = elem.attrib["value"]
                for checkbox in field_items:
                    assert isinstance(checkbox, Checkbox)
                    if checkbox._value == selected_value:
                        checkbox.checked = value
            else:
                form[field_name] = value
            self.last_form = form

    def submit(self, css_selector=""):
        """
        Submit the form. css_selector should refer to a form, or a button/input to use
        to submit the form, or "" for the last form accessed.
        """
        assert self.last_response is not None
        assert self.last_url is not None
        field_name = None
        if css_selector == "":
            assert self.last_form is not None
            form = self.last_form
        else:
            try:
                form = self._find_form_by_css_selector(self.last_response, css_selector)
                field_name = None
            except WebTestNoSuchElementException:
                form, field_name, _ = self._find_form_and_field_by_css_selector(
                    self.last_response,
                    css_selector,
                    require_name=False,
                    filter_selector="input[type=submit], button",
                )

        form_submission = form.prepare_submit(name=field_name)
        action_url = urllib.parse.urljoin(self.last_url, form_submission.action)
        if form_submission.method == "POST":
            # TODO do we need `enctype` here?
            self._set_response(self.client_post(action_url, data=form_submission.data))

    def _find_form_by_css_selector(self, response: PageResponse, css_selector: str) -> Form:
        pq = response.pq
        items = pq.find(css_selector)
        if any(item.tag == "form" for item in items):
            if len(items) > 1:
                raise WebTestMultipleElementsException(f"Found multiple forms matching {css_selector}")
            return self._match_form_elem_to_webtest_form(items[0], response)
        else:
            raise WebTestNoSuchElementException(f"Can't find form matching {css_selector}")

    def _find_form_and_field_by_css_selector(
        self, response: PageResponse, css_selector: str, filter_selector=None, require_name=True
    ) -> tuple[Form, str, HtmlElement]:
        pq = response.pq
        items = pq.find(css_selector)

        found: list[tuple[Form, str, HtmlElement]] = []
        if filter_selector:
            items = items.filter(filter_selector)
        for item in items:
            form_elem = self._find_parent_form(item)
            if form_elem is None:
                raise WebTestCantUseElement(f"Can't find form for input {css_selector}.")
            form = self._match_form_elem_to_webtest_form(form_elem, response)
            field = item.name if hasattr(item, "name") else item.attrib.get("name", None)
            if field is None and require_name:
                raise WebTestCantUseElement(f"Element {css_selector} needs 'name' attribute in order to use it")
            found.append((form, field, item))

        if len(found) > 1:
            if not all(f[0:2] == found[0][0:2] for f in found):
                raise WebTestMultipleElementsException(f"Multiple elements found matching '{css_selector}'")

        if len(found) > 0:
            return found[0]

        raise WebTestNoSuchElementException(f"Can't find element matching {css_selector} in response {response}.")

    def _find_parent_form(self, elem):
        p = elem.getparent()
        if p is None:
            return None
        if p.tag == "form":
            return p
        return self._find_parent_form(p)

    def _match_form_elem_to_webtest_form(self, form_elem, response: PageResponse) -> Form:
        pq = response.pq
        forms = pq("form")
        form_index = forms.index(form_elem)
        webtest_form = response.forms[form_index]
        form_sig = {
            "action": form_elem.attrib.get("action", ""),
            "id": form_elem.attrib.get("id", ""),
            "method": form_elem.attrib.get("method", "").lower(),
        }
        webtest_sig = {
            "action": getattr(webtest_form, "action", ""),
            "id": getattr(webtest_form, "id", ""),
            "method": getattr(webtest_form, "method", "").lower(),
        }
        webtest_sig = {k: v if v is not None else "" for k, v in webtest_sig.items()}
        assert form_sig == webtest_sig
        return webtest_form


class PageResponse:
    # Based on `TestResponse` from WebTest
    def __init__(self, response: Response) -> None:
        self.response = response

    @cached_property
    def pq(self) -> PyQuery:
        return PyQuery(self.response.content, parser="html")

    @cached_property
    def html(self):
        """
        Returns the response as a `BeautifulSoup
        <https://www.crummy.com/software/BeautifulSoup/bs3/documentation.html>`_
        object.

        Only works with HTML responses
        """
        soup = BeautifulSoup(self.response.content, "html.parser")
        return soup

    @cached_property
    def text(self) -> str:
        return self.html.text

    @cached_property
    def forms(self) -> dict[str | int, Form]:
        """
        Returns a dictionary containing all the forms in the pages as
        ``Form`` objects
        """
        forms: dict[str | int, Form] = {}
        form_texts = [str(f) for f in self.html("form")]
        for i, text in enumerate(form_texts):
            form = Form(text)
            forms[i] = form
            if form.id:
                forms[form.id] = form
        return forms


class WebTestNoSuchElementException(Exception):
    pass


class WebTestMultipleElementsException(Exception):
    pass


class WebTestCantUseElement(Exception):
    pass


class SeleniumCantUseElement(Exception):
    pass
