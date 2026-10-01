from fastapi import APIRouter, Query, Response
from typing import Optional
from datetime import datetime

from app.services.attendance_service import AttendanceService
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/export", tags=["Export"])

@router.get("/csv")
def export_csv(
    date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    records = AttendanceService.get_attendance_history(
        date=date,
        start_date=start_date,
        end_date=end_date,
        department=department,
        status=status,
        search=search,
        limit=5000
    )
    csv_bytes = ExportService.generate_csv(records)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"attendance_report_{timestamp}.csv"

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/excel")
def export_excel(
    date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    records = AttendanceService.get_attendance_history(
        date=date,
        start_date=start_date,
        end_date=end_date,
        department=department,
        status=status,
        search=search,
        limit=5000
    )
    excel_bytes = ExportService.generate_excel(records)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"attendance_report_{timestamp}.xlsx"

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
