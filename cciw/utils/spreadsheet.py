# Simple spreadsheet abstraction that does what we need for returning data in
# spreadsheets, supporting .xlsx

from abc import ABC, abstractmethod

import pandas as pd

from cciw.utils import xl


class SpreadsheetBuilder(ABC):
    mimetype: str
    file_ext: str

    @abstractmethod
    def to_bytes(self) -> bytes:
        raise NotImplementedError()


class SpreadsheetSimpleBuilder(SpreadsheetBuilder):
    @abstractmethod
    def add_sheet_with_header_row(self, name: str, headers: list[str], contents: list[list[str]]) -> None:
        raise NotImplementedError()


class SpreadsheetFromDataFrameBuilder(SpreadsheetBuilder):
    @abstractmethod
    def add_sheet_from_dataframe(self, name: str, dataframe: pd.DataFrame) -> None:
        raise NotImplementedError()


class ExcelBuilder(SpreadsheetSimpleBuilder):
    mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    file_ext = "xlsx"

    def __init__(self):
        self.wkbk = xl.empty_workbook()

    def add_sheet_with_header_row(self, name: str, headers: list[str], contents: list[list[str]]):
        xl.add_sheet_with_header_row(self.wkbk, name, headers, contents)

    def to_bytes(self) -> bytes:
        return xl.workbook_to_bytes(self.wkbk)


class ExcelFromDataFrameBuilder(SpreadsheetFromDataFrameBuilder):
    mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    file_ext = "xlsx"

    def __init__(self):
        # filename passed to force correct writer
        self.pd_writer = pd.ExcelWriter("tmp.xlsx")  # pylint: disable=abstract-class-instantiated

    def add_sheet_from_dataframe(self, name: str, dataframe: pd.DataFrame):
        dataframe.to_excel(self.pd_writer, sheet_name=name)

    def to_bytes(self) -> bytes:
        return xl.workbook_to_bytes(self.pd_writer.book)  # using ExcelWriter internals
