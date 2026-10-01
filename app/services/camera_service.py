import cv2
import time
import logging
import threading
from typing import Generator, Optional
import numpy as np

from app.ai.face_engine import face_engine
from app.services.attendance_service import AttendanceService

logger = logging.getLogger("ai_attendance.camera_service")

class CameraService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CameraService, cls).__new__(cls)
                cls._instance._cap = None
                cls._instance._is_running = False
                cls._instance._camera_index = 0
                cls._instance._read_lock = threading.Lock()
            return cls._instance

    def start_camera(self, camera_index: int = 0) -> bool:
        with self._read_lock:
            if self._cap is not None and self._cap.isOpened():
                if self._camera_index == camera_index:
                    return True
                self._cap.release()

            self._camera_index = camera_index
            # On Windows, try cv2.CAP_DSHOW or default
            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(camera_index)

            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                self._cap = cap
                self._is_running = True
                logger.info(f"Local camera {camera_index} initialized successfully.")
                return True
            else:
                logger.warning(f"Could not open local camera at index {camera_index}.")
                self._cap = None
                self._is_running = False
                return False

    def stop_camera(self):
        with self._read_lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            self._is_running = False
            logger.info("Local camera released.")

    def read_frame(self) -> Optional[np.ndarray]:
        with self._read_lock:
            if self._cap is None or not self._cap.isOpened():
                return None
            ret, frame = self._cap.read()
            if not ret or frame is None:
                return None
            return frame

    def generate_mjpeg_stream(self) -> Generator[bytes, None, None]:
        """Yields MJPEG frames with real-time AI recognition overlays and attendance marking."""
        if not self._is_running or self._cap is None:
            self.start_camera(self._camera_index)

        frame_count = 0
        last_results = []

        while self._is_running:
            frame = self.read_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            frame_count += 1
            # Run AI face detection every 3 frames for ultra smooth 30fps streaming
            if frame_count % 3 == 0 or not last_results:
                last_results = face_engine.process_frame(frame)
                date_str, time_str = AttendanceService.get_current_date_time()
                for res in last_results:
                    if res.get("recognized") and res.get("student_id"):
                        AttendanceService.mark_attendance(res["student_id"], confidence=res["score"])

            # Draw AI bounding boxes & labels
            display_frame = frame.copy()
            for res in last_results:
                x, y, w, h = res["box"]
                recognized = res.get("recognized", False)
                name = res.get("name", "Unknown")
                conf = res.get("confidence_pct", 0)

                # Color: Green for recognized, Red for unknown
                color = (46, 204, 113) if recognized else (50, 50, 220)
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)

                label = f"{name} ({conf}%)" if recognized else "Unknown"
                cv2.rectangle(display_frame, (x, y - 28), (x + w, y), color, -1)
                cv2.putText(
                    display_frame, label, (x + 6, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2
                )

            # Encode to JPEG
            ret, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.03)

camera_service = CameraService()
