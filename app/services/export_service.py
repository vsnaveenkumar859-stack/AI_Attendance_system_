import io
import csv
from datetime import datetime
from typing import List, Dict, Any
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

class ExportService:
    @staticmethod
    def generate_csv(records: List[Dict[str, Any]]) -> bytes:
        """Generates a CSV file as bytes with UTF-8 BOM encoding for Excel compatibility."""
        output = io.StringIO()
        # UTF-8 BOM
        output.write('\ufeff')

        fieldnames = [
            "ID", "Student ID", "Student Name", "Department", 
            "Date", "Time", "Status", "Confidence", "Method", "Notes"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for r in records:
            writer.writerow({
                "ID": r.get("id", ""),
                "Student ID": r.get("student_id", ""),
                "Student Name": r.get("student_name", ""),
                "Department": r.get("department", ""),
                "Date": r.get("date", ""),
                "Time": r.get("time", ""),
                "Status": r.get("status", ""),
                "Confidence": f"{round(float(r.get('confidence', 1.0)) * 100, 1)}%",
                "Method": r.get("method", "AI Face Recognition"),
                "Notes": r.get("notes", "")
            })

        return output.getvalue().encode('utf-8')

    @staticmethod
    def generate_excel(records: List[Dict[str, Any]]) -> bytes:
        """Generates a beautifully styled Excel workbook with summary cards and formatted records."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Attendance Records"

        # Styling definitions
        font_title = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
        fill_title = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")

        font_meta = Font(name="Calibri", size=10, italic=True, color="64748B")
        
        font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        fill_header = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")

        font_regular = Font(name="Calibri", size=11, color="0F172A")
        
        fill_present = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
        font_present = Font(name="Calibri", size=11, bold=True, color="166534")

        fill_late = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        font_late = Font(name="Calibri", size=11, bold=True, color="92400E")

        thin_border = Border(
            left=Side(style='thin', color="E2E8F0"),
            right=Side(style='thin', color="E2E8F0"),
            top=Side(style='thin', color="E2E8F0"),
            bottom=Side(style='thin', color="E2E8F0")
        )

        align_center = Alignment(horizontal="center", vertical="center")
        align_left = Alignment(horizontal="left", vertical="center")

        # 1. Title Banner
        ws.merge_cells("A1:I2")
        title_cell = ws["A1"]
        title_cell.value = "AI ATTENDANCE SYSTEM - OFFICIAL REPORT"
        title_cell.font = font_title
        title_cell.fill = fill_title
        title_cell.alignment = align_center

        # 2. Metadata / Summary Row
        gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_count = len(records)
        present_count = sum(1 for r in records if r.get("status") == "Present")
        late_count = sum(1 for r in records if r.get("status") == "Late")

        ws["A3"] = f"Generated On: {gen_time} | Total Records: {total_count} | Present: {present_count} | Late: {late_count}"
        ws["A3"].font = font_meta
        ws.merge_cells("A3:I3")

        # 3. Table Headers
        headers = [
            "#", "Student ID", "Student Name", "Department",
            "Date", "Time", "Status", "Confidence", "Method"
        ]
        start_row = 5
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=start_row, column=col_idx, value=header)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = thin_border

        # 4. Data Rows
        current_row = start_row + 1
        for idx, r in enumerate(records, 1):
            status = r.get("status", "Present")
            conf_val = f"{round(float(r.get('confidence', 1.0)) * 100, 1)}%"

            ws.cell(row=current_row, column=1, value=idx).alignment = align_center
            ws.cell(row=current_row, column=2, value=r.get("student_id", "")).alignment = align_center
            ws.cell(row=current_row, column=3, value=r.get("student_name", "")).alignment = align_left
            ws.cell(row=current_row, column=4, value=r.get("department", "")).alignment = align_left
            ws.cell(row=current_row, column=5, value=r.get("date", "")).alignment = align_center
            ws.cell(row=current_row, column=6, value=r.get("time", "")).alignment = align_center

            # Status cell with color badge
            status_cell = ws.cell(row=current_row, column=7, value=status)
            status_cell.alignment = align_center
            if status == "Present":
                status_cell.fill = fill_present
                status_cell.font = font_present
            else:
                status_cell.fill = fill_late
                status_cell.font = font_late

            ws.cell(row=current_row, column=8, value=conf_val).alignment = align_center
            ws.cell(row=current_row, column=9, value=r.get("method", "AI Face Recognition")).alignment = align_left

            for col_idx in range(1, 10):
                c = ws.cell(row=current_row, column=col_idx)
                c.border = thin_border
                if col_idx != 7:
                    c.font = font_regular

            current_row += 1

        # 5. Auto-fit column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.row < start_row:
                    continue
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()
