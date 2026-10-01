from fastapi import APIRouter
from .routes_students import router as students_router
from .routes_attendance import router as attendance_router
from .routes_export import router as export_router
from .routes_system import router as system_router

api_router = APIRouter()
api_router.include_router(students_router)
api_router.include_router(attendance_router)
api_router.include_router(export_router)
api_router.include_router(system_router)

__all__ = ["api_router"]
