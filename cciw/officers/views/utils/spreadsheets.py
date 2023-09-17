import openpyxl
from django.http import HttpResponse

from cciw.officers.views.utils.data_retention import DATA_RETENTION_NOTICES_TXT, DataRetentionNotice
from cciw.utils import xl
from cciw.utils.spreadsheet import ExcelBuilder


def spreadsheet_response(
    builder: ExcelBuilder,
    filename: str,
    *,
    notice: DataRetentionNotice | None,
) -> HttpResponse:
    output = builder.to_bytes()

    if notice is not None:
        workbook: openpyxl.Workbook = xl.workbook_from_bytes(builder.to_bytes())
        sheet = workbook.create_sheet("Notice", 0)
        c_header = sheet.cell(1, 1)
        c_header.value = "Data retention notice:"
        c_header.font = xl.header_font

        for row_idx, line in enumerate(notice_to_lines(notice), start=3):
            c = sheet.cell(row_idx, 1)
            c.value = line
            c.font = xl.default_font
        sheet.column_dimensions["A"].width = 100

        output = xl.workbook_to_bytes(workbook)
    response = HttpResponse(output, content_type=builder.mimetype)
    response["Content-Disposition"] = f"attachment; filename={filename}.{builder.file_ext}"
    return response


def notice_to_lines(notice: DataRetentionNotice) -> list[str]:
    txt = DATA_RETENTION_NOTICES_TXT[notice]
    return list(txt.split("\n"))
