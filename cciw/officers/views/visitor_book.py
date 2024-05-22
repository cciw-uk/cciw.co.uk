import base64
from io import BytesIO

import qrcode
import weasyprint
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.template.response import TemplateResponse

from cciw.cciwmain import common
from cciw.visitors.views import make_visitor_log_url


def visitor_book_utilities(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request,
        "cciw/officers/visitor_book_utilities.html",
        {
            "create_log_url": make_visitor_log_url(common.get_thisyear()),
            "title": "Visitor book utilities",
        },
    )


def text_to_qr_data_url(text):
    """
    Convert text to QR code and embed in data URL
    """
    img = qrcode.make(text)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def visitor_book_printout(request: HttpRequest) -> HttpResponse:
    year = common.get_thisyear()
    create_log_url = full_visitor_log_url(year)

    html_string = render_to_string(
        "cciw/officers/visitor_book_printout.html",
        context={
            "create_log_url": create_log_url,
            "year": year,
            "qrcode": text_to_qr_data_url(create_log_url),
        },
    )

    html = weasyprint.HTML(string=html_string)
    css = weasyprint.CSS(
        string="""
      @page { size: A4; margin: 2cm; }
      body { text-align: center;
             font-size: 18pt;
                 }
      h1 { font-size: 28pt; }
    """
    )
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="CCiW_camp_visitor_book_printout_{year}.pdf"'
    html.write_pdf(response, stylesheets=[css])
    return response


def full_visitor_log_url(year: int) -> str:
    return f"https://{common.get_current_domain()}{make_visitor_log_url(year)}"
