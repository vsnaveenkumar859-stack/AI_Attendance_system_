from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.attendance_service import AttendanceService
from app.database.models import AttendanceDB, StudentDB

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])

class FrameProcessRequest(BaseModel):
    image: str # Base64 image
    threshold: Optional[float] = None

class ManualAttendanceRequest(BaseModel):
    student_id: str
    date: Optional[str] = None
    time: Optional[str] = None
    status: str = "Present"
    notes: Optional[str] = "Manual Entry by Admin"

@router.post("/recognize-frame")
def process_frame(payload: FrameProcessRequest):
    """Real-time webcam frame processing endpoint for face detection, recognition, and attendance marking."""
    if not payload.image:
        raise HTTPException(status_code=400, detail="Image frame is required.")

    result = AttendanceService.process_live_frame(payload.image, payload.threshold)
    return {
        "success": True,
        "data": result
    }

@router.post("/mark-manual")
def mark_manual_attendance(payload: ManualAttendanceRequest):
    """Allows an administrator to manually mark attendance for a student."""
    res = AttendanceService.mark_attendance(
        student_id=payload.student_id,
        confidence=1.0,
        method="Manual Override",
        custom_date=payload.date,
        custom_time=payload.time,
        notes=payload.notes or ""
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.get("/history")
def get_attendance_history(
    date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(500, le=2000)
):
    records = AttendanceService.get_attendance_history(
        date=date,
        start_date=start_date,
        end_date=end_date,
        department=department,
        status=status,
        search=search,
        limit=limit
    )
    return {
        "success": True,
        "count": len(records),
        "records": records
    }

@router.get("/stats")
def get_dashboard_stats():
    stats = AttendanceService.get_dashboard_metrics()
    return {
        "success": True,
        "stats": stats
    }

@router.delete("/{record_id}")
def delete_attendance_record(record_id: int):
    success = AttendanceService.delete_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Attendance record not found.")
    return {
        "success": True,
        "message": f"Attendance record #{record_id} deleted successfully."
    }
