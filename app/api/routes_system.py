from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any

from app.database.models import SettingsDB, StudentDB
from app.ai.face_engine import face_engine
from app.services.camera_service import camera_service

router = APIRouter(prefix="/api/system", tags=["System"])

class SettingsPayload(BaseModel):
    late_cutoff_time: str
    cosine_threshold: str
    duplicate_cooldown: str
    system_title: str

class CameraControlPayload(BaseModel):
    action: str # "start" or "stop"
    camera_index: int = 0

@router.get("/settings")
def get_settings():
    return {
        "success": True,
        "settings": SettingsDB.get_all_settings()
    }

@router.post("/settings")
def update_settings(payload: SettingsPayload):
    SettingsDB.update_setting("late_cutoff_time", payload.late_cutoff_time)
    SettingsDB.update_setting("cosine_threshold", payload.cosine_threshold)
    SettingsDB.update_setting("duplicate_cooldown", payload.duplicate_cooldown)
    SettingsDB.update_setting("system_title", payload.system_title)

    try:
        new_thresh = float(payload.cosine_threshold)
        face_engine.set_threshold(new_thresh)
    except ValueError:
        pass

    return {
        "success": True,
        "message": "System settings updated successfully."
    }

@router.get("/status")
def get_system_status():
    student_count = StudentDB.count_students()
    total_embeddings = sum(len(embs) for embs in face_engine.known_embeddings.values())
    return {
        "success": True,
        "ai_engine": {
            "use_sface": face_engine.use_sface,
            "detector_loaded": face_engine.detector is not None,
            "recognizer_loaded": face_engine.recognizer is not None,
            "threshold": face_engine.threshold,
            "registered_students": student_count,
            "cached_embeddings": total_embeddings
        },
        "camera": {
            "is_running": camera_service._is_running,
            "camera_index": camera_service._camera_index
        }
    }

@router.post("/camera/control")
def camera_control(payload: CameraControlPayload):
    if payload.action == "start":
        started = camera_service.start_camera(payload.camera_index)
        return {"success": started, "message": "Camera started" if started else "Failed to open camera"}
    elif payload.action == "stop":
        camera_service.stop_camera()
        return {"success": True, "message": "Camera stopped"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

@router.get("/camera/stream")
def camera_stream():
    """MJPEG stream endpoint for server-side local webcam."""
    return StreamingResponse(
        camera_service.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
