import time
import base64
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from app.database.models import AttendanceDB, StudentDB, SettingsDB
from app.ai.face_engine import face_engine

class AttendanceService:
    # Memory cache for alert cooldowns: student_id -> last_notification_timestamp
    _alert_cooldowns: Dict[str, float] = {}

    @classmethod
    def get_current_date_time(cls) -> Tuple[str, str]:
        now = datetime.now()
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    @classmethod
    def mark_attendance(
        cls,
        student_id: str,
        confidence: float = 1.0,
        method: str = "AI Face Recognition",
        custom_time: Optional[str] = None,
        custom_date: Optional[str] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Marks attendance for a student with duplicate prevention on the same calendar day.
        """
        student_id = student_id.strip().upper()
        student = StudentDB.get_student_by_id(student_id)
        if not student:
            return {
                "success": False,
                "status": "not_found",
                "message": f"Student ID '{student_id}' is not registered."
            }

        date_str, time_str = cls.get_current_date_time()
        if custom_date:
            date_str = custom_date
        if custom_time:
            time_str = custom_time

        # Check for duplicate on the same day
        existing = AttendanceDB.has_attended_today(student_id, date_str)
        if existing:
            return {
                "success": False,
                "status": "duplicate",
                "message": f"Attendance already marked for {student['name']} today at {existing['time']}.",
                "student_id": student_id,
                "student_name": student["name"],
                "department": student["department"],
                "time": existing["time"],
                "date": existing["date"],
                "record": existing
            }

        # Check late cutoff time
        late_cutoff = SettingsDB.get_setting("late_cutoff_time", "09:30")
        try:
            cutoff_h, cutoff_m = map(int, late_cutoff.split(":"))
            current_h, current_m = map(int, time_str.split(":")[:2])
            status = "Late" if (current_h > cutoff_h or (current_h == cutoff_h and current_m > cutoff_m)) else "Present"
        except Exception:
            status = "Present"

        record_id = AttendanceDB.record_attendance(
            student_id=student_id,
            student_name=student["name"],
            department=student["department"],
            date_str=date_str,
            time_str=time_str,
            confidence=confidence,
            status=status,
            method=method,
            notes=notes
        )

        if record_id:
            return {
                "success": True,
                "status": "marked",
                "message": f"Attendance marked as '{status}' for {student['name']}.",
                "record_id": record_id,
                "student_id": student_id,
                "student_name": student["name"],
                "department": student["department"],
                "status_text": status,
                "date": date_str,
                "time": time_str,
                "confidence": round(float(confidence), 3)
            }
        else:
            # Fallback if race condition hit unique constraint
            existing = AttendanceDB.has_attended_today(student_id, date_str)
            return {
                "success": False,
                "status": "duplicate",
                "message": f"Attendance already marked for {student['name']} today.",
                "student_id": student_id,
                "student_name": student["name"],
                "record": existing
            }

    @classmethod
    def process_live_frame(cls, base64_image: str, threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        Receives a base64 encoded frame from webcam/browser, detects and recognizes faces,
        and marks attendance for recognized students.
        """
        try:
            if "," in base64_image:
                base64_image = base64_image.split(",")[1]
            img_bytes = base64.b64decode(base64_image)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception:
            return {"faces": [], "events": []}

        if img is None or img.size == 0:
            return {"faces": [], "events": []}

        now_sec = time.time()
        cooldown_sec = float(SettingsDB.get_setting("duplicate_cooldown", "8"))
        results = face_engine.process_frame(img, threshold)

        faces_output = []
        attendance_events = []

        date_str, time_str = cls.get_current_date_time()

        for res in results:
            box = res["box"]
            student_id = res.get("student_id")
            name = res.get("name", "Unknown")
            conf_pct = res.get("confidence_pct", 0.0)
            score = res.get("score", 0.0)
            recognized = res.get("recognized", False)

            status_type = "unknown"
            event_message = ""
            should_alert = False

            if recognized and student_id:
                # Check DB for duplicate today
                existing = AttendanceDB.has_attended_today(student_id, date_str)
                last_alert_time = cls._alert_cooldowns.get(student_id, 0.0)
                is_cooldown_expired = (now_sec - last_alert_time) > cooldown_sec

                if existing:
                    status_type = "already_marked"
                    event_message = f"Already marked today at {existing['time']}"
                    if is_cooldown_expired:
                        should_alert = True
                        cls._alert_cooldowns[student_id] = now_sec
                        attendance_events.append({
                            "type": "duplicate",
                            "student_id": student_id,
                            "name": name,
                            "department": res.get("department", ""),
                            "time": existing["time"],
                            "message": event_message
                        })
                else:
                    # Mark attendance!
                    mark_res = cls.mark_attendance(student_id, confidence=score, method="AI Face Recognition")
                    status_type = "newly_marked"
                    event_message = f"Marked {mark_res.get('status_text', 'Present')} at {mark_res.get('time', time_str)}"
                    should_alert = True
                    cls._alert_cooldowns[student_id] = now_sec
                    attendance_events.append({
                        "type": "marked",
                        "student_id": student_id,
                        "name": name,
                        "department": res.get("department", ""),
                        "status": mark_res.get("status_text", "Present"),
                        "time": mark_res.get("time", time_str),
                        "confidence": conf_pct,
                        "message": event_message
                    })
            else:
                status_type = "unknown"
                event_message = "Unregistered face"

            faces_output.append({
                "box": box,
                "student_id": student_id,
                "name": name,
                "department": res.get("department", ""),
                "score": score,
                "confidence_pct": conf_pct,
                "status_type": status_type,
                "message": event_message,
                "should_alert": should_alert
            })

        return {
            "faces": faces_output,
            "events": attendance_events,
            "timestamp": time_str
        }

    @staticmethod
    def get_attendance_history(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        department: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        return AttendanceDB.get_attendance_records(
            date=date,
            start_date=start_date,
            end_date=end_date,
            department=department,
            status=status,
            search=search,
            limit=limit
        )

    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        today_date = datetime.now().strftime("%Y-%m-%d")
        return AttendanceDB.get_dashboard_stats(today_date)

    @staticmethod
    def delete_record(record_id: int) -> bool:
        return AttendanceDB.delete_record(record_id)
