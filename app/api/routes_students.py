from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any

from app.services.student_service import StudentService
from app.database.models import StudentDB

router = APIRouter(prefix="/api/students", tags=["Students"])

class StudentCreateRequest(BaseModel):
    student_id: str
    name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    department: str
    year_semester: Optional[str] = ""
    gender: Optional[str] = "Other"
    images: List[str]  # Base64 encoded images

class StudentUpdateRequest(BaseModel):
    name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    department: str
    year_semester: Optional[str] = ""
    gender: Optional[str] = "Other"

class ReEnrollRequest(BaseModel):
    images: List[str]

@router.post("/register")
def register_student(payload: StudentCreateRequest):
    data = payload.model_dump()
    images = data.pop("images", [])

    success, message, student = StudentService.register_student(data, images)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message,
        "student": student
    }

@router.get("")
def list_students(
    search: Optional[str] = Query(None),
    department: Optional[str] = Query(None)
):
    students = StudentService.get_all_students(search=search, department=department)
    return {
        "success": True,
        "count": len(students),
        "students": students
    }

@router.get("/departments/list")
def list_departments():
    departments = StudentDB.get_all_departments()
    return {
        "success": True,
        "departments": departments
    }

@router.get("/{student_id}")
def get_student(student_id: str):
    student = StudentService.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found.")
    return {
        "success": True,
        "student": student
    }

@router.put("/{student_id}")
def update_student(student_id: str, payload: StudentUpdateRequest):
    success = StudentService.update_student(student_id, payload.model_dump())
    if not success:
        raise HTTPException(status_code=404, detail="Student not found or not updated.")
    return {
        "success": True,
        "message": "Student details updated successfully."
    }

@router.delete("/{student_id}")
def delete_student(student_id: str):
    success = StudentService.delete_student(student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Student not found.")
    return {
        "success": True,
        "message": f"Student '{student_id}' and all associated face data deleted successfully."
    }

@router.post("/{student_id}/re-enroll")
def re_enroll_student_face(student_id: str, payload: ReEnrollRequest):
    if not payload.images:
        raise HTTPException(status_code=400, detail="At least one image is required for re-enrollment.")
    success, message = StudentService.re_enroll_faces(student_id, payload.images)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {
        "success": True,
        "message": message
    }
