import os
import cv2
import json
import logging
import threading
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

from app.config import (
    YUNET_MODEL_PATH,
    SFACE_MODEL_PATH,
    FACES_DIR,
    EMBEDDINGS_CACHE_PATH,
    DEFAULT_COSINE_THRESHOLD,
    DEFAULT_DETECTION_CONFIDENCE,
    DEFAULT_NMS_THRESHOLD
)
from app.ai.model_manager import ensure_models

logger = logging.getLogger("ai_attendance.face_engine")


class FaceEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FaceEngine, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.detector = None
        self.recognizer = None
        self.haar_cascade = None
        self.lbph_recognizer = None
        self.use_sface = True

        # In-memory database of student embeddings
        # Key: student_id -> List of 128-d numpy arrays
        self.known_embeddings: Dict[str, List[np.ndarray]] = {}
        # Key: student_id -> dict with name, department, photo
        self.known_students_meta: Dict[str, Dict[str, Any]] = {}

        self.current_input_size = (320, 320)
        self.threshold = DEFAULT_COSINE_THRESHOLD

        self._init_models()
        self.reload_known_faces()
        self._initialized = True

    def _init_models(self):
        """Initializes Face Detection and Face Recognition models."""
        ensure_models()

        # 1. Initialize Deep Learning YuNet & SFace
        if YUNET_MODEL_PATH.exists() and SFACE_MODEL_PATH.exists():
            try:
                self.detector = cv2.FaceDetectorYN.create(
                    model=str(YUNET_MODEL_PATH),
                    config="",
                    input_size=self.current_input_size,
                    score_threshold=DEFAULT_DETECTION_CONFIDENCE,
                    nms_threshold=DEFAULT_NMS_THRESHOLD,
                    top_k=5000,
                    backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
                    target_id=cv2.dnn.DNN_TARGET_CPU
                )
                self.recognizer = cv2.FaceRecognizerSF.create(
                    model=str(SFACE_MODEL_PATH),
                    config="",
                    backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
                    target_id=cv2.dnn.DNN_TARGET_CPU
                )
                self.use_sface = True
                logger.info("Successfully loaded YuNet & SFace Deep Learning Face Engine!")
            except Exception as e:
                logger.warning(f"Error loading YuNet/SFace models: {e}. Falling back to Haar+LBPH.")
                self.use_sface = False
        else:
            self.use_sface = False

        # 2. Initialize Haar Cascade as fallback
        haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if os.path.exists(haar_path):
            self.haar_cascade = cv2.CascadeClassifier(haar_path)
            if hasattr(cv2.face, "LBPHFaceRecognizer_create"):
                self.lbph_recognizer = cv2.face.LBPHFaceRecognizer_create()
            logger.info("Loaded Haar Cascade face detector fallback.")

    def set_threshold(self, threshold: float):
        self.threshold = float(threshold)

    def detect_faces(self, image_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects faces in the given BGR image.
        Returns a list of dicts with:
        - 'box': [x, y, w, h] (clamped within image boundary)
        - 'raw_face': the raw 15-dim face array from YuNet (or None for Haar)
        - 'score': confidence score
        """
        h, w = image_bgr.shape[:2]
        detected = []

        if self.use_sface and self.detector is not None:
            # YuNet requires input size matching current frame dimensions
            if self.current_input_size != (w, h):
                self.detector.setInputSize((w, h))
                self.current_input_size = (w, h)

            try:
                retval, faces = self.detector.detect(image_bgr)
                if retval > 0 and faces is not None:
                    for face in faces:
                        score = float(face[-1])
                        fx, fy, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                        # Clamp bounding box
                        fx = max(0, fx)
                        fy = max(0, fy)
                        fw = min(w - fx, fw)
                        fh = min(h - fy, fh)
                        if fw > 20 and fh > 20:
                            detected.append({
                                "box": [fx, fy, fw, fh],
                                "raw_face": face,
                                "score": round(score, 3)
                            })
                    return detected
            except Exception as e:
                logger.error(f"YuNet detection error: {e}")

        # Fallback to Haar Cascade
        if self.haar_cascade is not None:
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            faces = self.haar_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            for (fx, fy, fw, fh) in faces:
                detected.append({
                    "box": [int(fx), int(fy), int(fw), int(fh)],
                    "raw_face": None,
                    "score": 0.85
                })

        return detected

    def extract_feature(self, image_bgr: np.ndarray, face_info: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Extracts 128-d feature vector from face using SFace.
        If raw_face landmark info is available, uses alignCrop; otherwise crops and resizes to 112x112.
        """
        if not self.use_sface or self.recognizer is None:
            return None

        try:
            raw_face = face_info.get("raw_face")
            if raw_face is not None:
                aligned = self.recognizer.alignCrop(image_bgr, raw_face)
            else:
                x, y, w, h = face_info["box"]
                crop = image_bgr[y:y+h, x:x+w]
                if crop.size == 0:
                    return None
                aligned = cv2.resize(crop, (112, 112))

            feat = self.recognizer.feature(aligned)
            # Normalize vector
            norm = np.linalg.norm(feat)
            if norm > 0:
                feat = feat / norm
            return feat.astype(np.float32)
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return None

    def match_feature(self, feature: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Matches a single face feature against all enrolled students.
        Returns: (best_student_id, cosine_score) or (None, 0.0)
        """
        if not self.known_embeddings or feature is None:
            return None, 0.0

        best_student_id = None
        best_score = -1.0

        feat_flat = feature.flatten()

        for student_id, emb_list in self.known_embeddings.items():
            for emb in emb_list:
                # Cosine similarity between two unit vectors is simply the dot product
                score = float(np.dot(feat_flat, emb.flatten()))
                if score > best_score:
                    best_score = score
                    best_student_id = student_id

        if best_score >= self.threshold:
            return best_student_id, best_score

        return None, max(0.0, best_score)

    def process_frame(self, image_bgr: np.ndarray, current_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Full pipeline for a video frame:
        Detects faces, extracts embeddings, matches with known students, and returns recognition results.
        """
        threshold = current_threshold if current_threshold is not None else self.threshold
        faces = self.detect_faces(image_bgr)
        results = []

        for face in faces:
            box = face["box"]
            feature = self.extract_feature(image_bgr, face)
            
            student_id = None
            score = 0.0

            if feature is not None:
                student_id, score = self.match_feature(feature)

            if student_id and score >= threshold:
                meta = self.known_students_meta.get(student_id, {})
                # Normalize confidence to 0-100%
                # Cosine range for SFace: ~0.36 to ~0.80+
                conf_pct = min(100.0, max(50.0, round(((score - 0.30) / 0.50) * 100, 1)))
                results.append({
                    "box": box,
                    "student_id": student_id,
                    "name": meta.get("name", "Student " + student_id),
                    "department": meta.get("department", ""),
                    "score": round(score, 3),
                    "confidence_pct": conf_pct,
                    "recognized": True
                })
            else:
                results.append({
                    "box": box,
                    "student_id": None,
                    "name": "Unknown",
                    "department": "",
                    "score": round(score, 3),
                    "confidence_pct": 0.0,
                    "recognized": False
                })

        return results

    def enroll_student(self, student_id: str, name: str, department: str, images_bgr: List[np.ndarray]) -> int:
        """
        Enrolls a student with one or multiple captured face images.
        Extracts features, stores raw crops in data/faces/{student_id}/, and updates in-memory embeddings.
        Returns the number of valid face samples successfully enrolled.
        """
        student_id = student_id.strip().upper()
        student_dir = FACES_DIR / student_id
        student_dir.mkdir(parents=True, exist_ok=True)

        new_embeddings = []
        valid_count = 0

        for i, img in enumerate(images_bgr):
            faces = self.detect_faces(img)
            if not faces:
                continue

            # Pick the largest face in case of multiple
            largest_face = max(faces, key=lambda f: f["box"][2] * f["box"][3])
            feat = self.extract_feature(img, largest_face)

            if feat is not None:
                new_embeddings.append(feat)
                valid_count += 1

                # Save face crop image
                x, y, w, h = largest_face["box"]
                crop = img[y:y+h, x:x+w]
                if crop.size > 0:
                    filename = f"sample_{i+1}.jpg"
                    cv2.imwrite(str(student_dir / filename), crop)

        if new_embeddings:
            with self._lock:
                if student_id not in self.known_embeddings:
                    self.known_embeddings[student_id] = []
                self.known_embeddings[student_id].extend(new_embeddings)
                self.known_students_meta[student_id] = {
                    "name": name,
                    "department": department,
                    "photo": f"/static/faces/{student_id}/sample_1.jpg" if (student_dir / "sample_1.jpg").exists() else ""
                }
            self.save_embeddings_cache()

        return valid_count

    def reload_known_faces(self):
        """Loads and builds the embeddings dictionary from the faces directory."""
        with self._lock:
            self.known_embeddings.clear()
            self.known_students_meta.clear()

        # Fetch students metadata from database if available
        from app.database.models import StudentDB
        from app.database.db import init_db
        try:
            students = StudentDB.get_all_students()
        except Exception:
            init_db()
            students = StudentDB.get_all_students()
        student_meta_map = {s["student_id"]: s for s in students}

        loaded_count = 0
        embeddings_dict = {}

        if FACES_DIR.exists():
            for student_folder in FACES_DIR.iterdir():
                if not student_folder.is_dir():
                    continue

                student_id = student_folder.name.upper()
                embeddings_dict[student_id] = []

                for img_file in student_folder.glob("*.jpg"):
                    try:
                        img = cv2.imread(str(img_file))
                        if img is None:
                            continue

                        faces = self.detect_faces(img)
                        if faces:
                            largest = max(faces, key=lambda f: f["box"][2] * f["box"][3])
                            feat = self.extract_feature(img, largest)
                            if feat is not None:
                                embeddings_dict[student_id].append(feat)
                                loaded_count += 1
                        else:
                            # Direct resize if already cropped
                            crop = cv2.resize(img, (112, 112))
                            if self.use_sface and self.recognizer:
                                feat = self.recognizer.feature(crop)
                                norm = np.linalg.norm(feat)
                                if norm > 0:
                                    feat = feat / norm
                                embeddings_dict[student_id].append(feat.astype(np.float32))
                                loaded_count += 1
                    except Exception as e:
                        logger.warning(f"Error reading image {img_file}: {e}")

                meta = student_meta_map.get(student_id, {})
                primary_photo = f"/static/faces/{student_id}/sample_1.jpg" if (student_folder / "sample_1.jpg").exists() else ""
                self.known_students_meta[student_id] = {
                    "name": meta.get("name", student_id),
                    "department": meta.get("department", "General"),
                    "photo": primary_photo
                }

        with self._lock:
            self.known_embeddings = embeddings_dict

        logger.info(f"Loaded {loaded_count} face embeddings for {len(self.known_embeddings)} students.")
        self.save_embeddings_cache()

    def remove_student(self, student_id: str):
        """Removes student from memory and face storage."""
        student_id = student_id.strip().upper()
        with self._lock:
            if student_id in self.known_embeddings:
                del self.known_embeddings[student_id]
            if student_id in self.known_students_meta:
                del self.known_students_meta[student_id]

        import shutil
        student_dir = FACES_DIR / student_id
        if student_dir.exists():
            shutil.rmtree(student_dir, ignore_errors=True)

        self.save_embeddings_cache()

    def save_embeddings_cache(self):
        """Serializes current embeddings to disk cache."""
        try:
            cache = {}
            for sid, feats in self.known_embeddings.items():
                cache[sid] = [f.tolist() for f in feats]
            with open(EMBEDDINGS_CACHE_PATH, "w") as f:
                json.dump(cache, f)
        except Exception as e:
            logger.error(f"Failed to save embeddings cache: {e}")


# Global face engine accessor
face_engine = FaceEngine()
