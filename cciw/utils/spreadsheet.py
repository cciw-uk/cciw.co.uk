# Simple spreadsheet abstraction that does what we need for returning data in
# spreadsheets, supporting .xls and .ods

import xlwt
import ezodf2

from cciw.utils import xl


class ExcelFormatter(object):
    mimetype = "application/vnd.ms-excel"
    file_ext = "xls"

    def __init__(self):
        # A formatter is only be used once, so we can create workbook here.
        self.wkbk = xlwt.Workbook(encoding='utf8')

    def add_sheet_with_header_row(self, name, headers, contents):
        xl.add_sheet_with_header_row(self.wkbk, name, headers, contents)

    def to_bytes(self):
        return xl.workbook_to_bytes(self.wkbk)


class OdsFormatter(object):
    mimetype = "application/vnd.oasis.opendocument.spreadsheet"
    file_ext = "ods"

    def __init__(self):
        self.wkbk = ezodf2.newdoc("ods", "workbook")

    def add_sheet_with_header_row(self, name, headers, contents):
        headers = list(headers)
        contents = list(contents)
        sheet = ezodf2.Sheet(name, size=(len(contents) + 1, len(headers)))
        self.wkbk.sheets += sheet
        for c, header in enumerate(headers):
            sheet[0, c].set_value(header)
        for r, row in enumerate(contents):
            for c, val in enumerate(row):
                if val is not None:
                    sheet[r + 1, c].set_value(val)

    def to_bytes(self):
        return self.wkbk.tobytes()
