"""
Simplified xlwt interface
"""
from copy import deepcopy
from datetime import datetime, date
from io import BytesIO

from django.utils import timezone
from pytz import UTC

import xlwt


def add_sheet_with_header_row(wkbk, name, headers, contents):
    """
    Utility function for adding sheet to xlwt workbook.
    sheet_header is an iterable of strings
    sheet_contents is an iterable of rows, where each row is an interable of strings
    """
    wksh = wkbk.add_sheet(name)

    normal_style = xlwt.XFStyle()
    normal_style.alignment.vert = xlwt.Alignment.VERT_CENTER
    normal_style.borders.left = xlwt.Borders.THIN
    normal_style.borders.right = xlwt.Borders.THIN
    normal_style.borders.top = xlwt.Borders.THIN
    normal_style.borders.bottom = xlwt.Borders.THIN

    wrapped_style = deepcopy(normal_style)
    wrapped_style.alignment.wrap = True

    url_style = deepcopy(normal_style)
    url_style.font.colour_index = 12  # blue

    date_style = deepcopy(normal_style)
    date_style.num_format_str = 'YYYY/MM/DD'

    style_header = deepcopy(normal_style)
    font_header = xlwt.Font()
    font_header.bold = True
    style_header.font = font_header

    for c, header in enumerate(headers):
        wksh.write(0, c, header, style=style_header)

    for r, row in enumerate(contents):
        row_height = normal_style.font.height
        for c, val in enumerate(row):
            if isinstance(val, str):
                # normalise newlines to style expected by Excel
                val = val.replace('\r\n', '\n')

            if isinstance(val, (datetime, date)):
                style = date_style
                if isinstance(val, datetime):
                    if timezone.is_aware(val):
                        val = timezone.make_naive(val, UTC)
            else:
                style = normal_style
                if isinstance(val, str) and '\n' in val:
                    # This is needed or Excel displays box character for
                    # newlines.
                    style = wrapped_style
                    # Set height to be able to see all lines
                    row_height = max(row_height, normal_style.font.height * (val.count('\n') + 1))
                if looks_like_url(val):
                    val = xlwt.Formula('HYPERLINK("{0}"; "{1}")'.format(val, val))
                    style = url_style
            wksh.write(r + 1, c, val, style=style)
        wksh.rows[r + 1].height = row_height + 100  # fudge for margin, based on OpenOffice


def looks_like_url(val):
    return (isinstance(val, str) and
            " " not in val and
            "\n" not in val and
            (val.startswith("http://") or
             val.startswith("https://")))


def workbook_to_bytes(wkbk):
    s = BytesIO()
    wkbk.save(s)
    s.seek(0)
    return s.read()
