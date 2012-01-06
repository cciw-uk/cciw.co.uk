# Simple spreadsheet abstraction that does what we need for returning data in
# spreadsheets, supporting .xls and .ods

import xlwt

from cciw.utils import xl

class ExcelFormatter(object):
    mimetype = "application/vnd.ms-excel"
    file_ext = "xls"

    def __init__(self):
        # A formatter is only be used once, so we can create workbook here.
        self.wkbk = xlwt.Workbook(encoding='utf8')

    def add_sheet_with_header_row(self, name, headers, contents):
        xl.add_sheet_with_header_row(self.wkbk, name, headers, contents)

    def to_string(self):
        return xl.workbook_to_string(self.wkbk)
