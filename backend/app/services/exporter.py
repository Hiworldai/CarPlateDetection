from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from ..models import RecognitionRecord


def build_excel(records: list[RecognitionRecord]) -> BytesIO:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "recognitions"
    sheet.append(["识别时间", "车牌号", "检测置信度", "OCR置信度", "来源", "源文件", "车牌截图", "整帧截图"])

    for record in records:
        sheet.append(
            [
                record.recognized_at.strftime("%Y-%m-%d %H:%M:%S") if record.recognized_at else "",
                record.plate_text,
                record.det_score,
                record.rec_score,
                record.source_type,
                record.source_filename,
                record.plate_image_path,
                record.frame_image_path,
            ]
        )

    for column_cells in sheet.columns:
        column = column_cells[0].column_letter
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column].width = min(max(max_length + 2, 12), 48)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output
