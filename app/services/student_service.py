import cv2
import base64
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from app.config import FACES_DIR
from app.database.models import StudentDB
from app.ai.face_engine import face_engine

class StudentService:
    @staticmethod
    def decode_base64_image(b64_str: str) -> Optional[np.ndarray]:
        """Decodes a base64 encoded image string (data:image/jpeg;base64,...) to OpenCV BGR numpy array."""
        try:
            if "," in b64_str:
                b64_str = b64_str.split(",")[1]
            img_bytes = base64.b64decode(b64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception:
            return None

    @classmethod
    def register_student(
        cls,
        data: Dict[str, Any],
        base64_images: List[str]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validates, enrolls face samples, and registers a student in DB.
        Returns: (success: bool, message: str, student_dict: Optional[dict])
        """
        student_id = data.get("student_id", "").strip().upper()
        name = data.get("name", "").strip()
        department = data.get("department", "").strip()

        if not student_id or not name or not department:
            return False, "Student ID, Name, and Department are required.", None

        # Check for existing student ID
        existing = StudentDB.get_student_by_id(student_id)
        if existing:
            return False, f"A student with ID '{student_id}' already exists.", None

        # Decode face images
        bgr_images = []
        for b64 in base64_images:
            if not b64:
                continue
            decoded = cls.decode_base64_image(b64)
            if decoded is not None and decoded.size > 0:
                bgr_images.append(decoded)

        if not bgr_images:
            return False, "At least one valid face photo is required for enrollment.", None

        # Enroll face samples
        enrolled_count = face_engine.enroll_student(
            student_id=student_id,
            name=name,
            department=department,
            images_bgr=bgr_images
        )

        if enrolled_count == 0:
            return False, "Could not detect a clear face in the captured images. Please look directly at the camera with good lighting.", None

        primary_photo_path = f"/static/faces/{student_id}/sample_1.jpg"

        record_data = {
            "student_id": student_id,
            "name": name,
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "department": department,
            "year_semester": data.get("year_semester", ""),
            "gender": data.get("gender", "Other"),
            "face_samples_count": enrolled_count,
            "primary_photo_path": primary_photo_path
        }

        try:
            StudentDB.create_student(record_data)
            created_student = StudentDB.get_student_by_id(student_id)
            return True, f"Student '{name}' registered successfully with {enrolled_count} face sample(s)!", created_student
        except Exception as e:
            # Clean up enrolled face data on failure
            face_engine.remove_student(student_id)
            return False, f"Database error during registration: {str(e)}", None

    @classmethod
    def re_enroll_faces(
        cls,
        student_id: str,
        base64_images: List[str]
    ) -> Tuple[bool, str]:
        """Re-enrolls face samples for an existing student."""
        student = StudentDB.get_student_by_id(student_id)
        if not student:
            return False, f"Student '{student_id}' not found."

        bgr_images = []
        for b64 in base64_images:
            decoded = cls.decode_base64_image(b64)
            if decoded is not None and decoded.size > 0:
                bgr_images.append(decoded)

        if not bgr_images:
            return False, "No valid face images provided."

        # Clear existing face photos
        face_engine.remove_student(student_id)

        enrolled_count = face_engine.enroll_student(
            student_id=student_id,
            name=student["name"],
            department=student["department"],
            images_bgr=bgr_images
        )

        if enrolled_count == 0:
            return False, "Could not detect a face in the new images."

        primary_photo_path = f"/static/faces/{student_id}/sample_1.jpg"
        StudentDB.update_face_count(student_id, enrolled_count, primary_photo_path)
        return True, f"Successfully re-enrolled {enrolled_count} face sample(s) for {student['name']}."

    @staticmethod
    def get_all_students(search: Optional[str] = None, department: Optional[str] = None):
        return StudentDB.get_all_students(search, department)

    @staticmethod
    def get_student(student_id: str):
        return StudentDB.get_student_by_id(student_id)

    @staticmethod
    def update_student(student_id: str, data: Dict[str, Any]):
        return StudentDB.update_student(student_id, data)

    @staticmethod
    def delete_student(student_id: str) -> bool:
        face_engine.remove_student(student_id)
        return StudentDB.delete_student(student_id)
