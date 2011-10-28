"""
Simplified xlwt interface
"""
from datetime import datetime, date
import xlwt


def add_sheet_with_header_row(wkbk, name, headers, contents):
    """
    sheet_header is an iterable of strings
    sheet_contents is an iterable of rows, where each row is an interable of strings
    """
    wksh = wkbk.add_sheet(name)

    font_header = xlwt.Font()
    font_header.bold = True
    style_header = xlwt.XFStyle()
    style_header.font = font_header
    for c, header in enumerate(headers):
        wksh.write(0, c, header, style=style_header)

    date_style = xlwt.XFStyle()
    date_style.num_format_str = 'YYYY/MM/DD'

    for r, row in enumerate(contents):
        for c, val in enumerate(row):
            if isinstance(val, (datetime, date)):
                style = date_style
            else:
                style = xlwt.Style.default_style
            wksh.write(r + 1, c, val, style=style)
