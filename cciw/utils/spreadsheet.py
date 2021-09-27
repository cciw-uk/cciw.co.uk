# Simple spreadsheet abstraction that does what we need for returning data in
# spreadsheets, supporting .xls and .ods

import ezodf2
import pandas as pd
import xlwt

from cciw.utils import xl


class ExcelFormatter:
    mimetype = "application/vnd.ms-excel"
    file_ext = "xls"

    def __init__(self):
        # A formatter is only be used once
        self.pd_writer = None
        self.wkbk = None

    def add_sheet_with_header_row(self, name, headers, contents):
        self.ensure_wkbk()
        xl.add_sheet_with_header_row(self.wkbk, name, headers, contents)

    def add_sheet_from_dataframe(self, name, dataframe):
        self.ensure_pd_writer()
        dataframe.to_excel(self.pd_writer, sheet_name=name)

    def to_bytes(self):
        if self.pd_writer:
            return xl.workbook_to_bytes(self.pd_writer.book)  # using ExcelWriter internals
        return xl.workbook_to_bytes(self.wkbk)

    def ensure_wkbk(self):
        self.ensure_not_pd_writer()
        if self.wkbk is None:
            self.wkbk = xlwt.Workbook(encoding="utf8")

    def ensure_not_wkbk(self):
        if self.wkbk is not None:
            raise Exception("User either add_sheet_with_header_row or add_sheet_from_dataframe, not both")

    def ensure_pd_writer(self):
        self.ensure_not_wkbk()
        if self.pd_writer is None:
            self.pd_writer = pd.ExcelWriter("tmp.xls")  # filename to force _XlwtWriter

    def ensure_not_pd_writer(self):
        if self.pd_writer is not None:
            raise Exception("User either add_sheet_with_header_row or add_sheet_from_dataframe, not both")


class OdsFormatter:
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

    def add_sheet_from_dataframe(self, name, dataframe):
        raise NotImplementedError()

    def to_bytes(self):
        return self.wkbk.tobytes()
