import os
import requests
import logging
from pathlib import Path
from app.config import YUNET_MODEL_URL, SFACE_MODEL_URL, YUNET_MODEL_PATH, SFACE_MODEL_PATH

logger = logging.getLogger("ai_attendance.model_manager")

def ensure_models() -> bool:
    """Ensures YuNet and SFace models are downloaded and present."""
    success = True
    for name, url, path in [
        ("YuNet Face Detector", YUNET_MODEL_URL, YUNET_MODEL_PATH),
        ("SFace Face Recognizer", SFACE_MODEL_URL, SFACE_MODEL_PATH)
    ]:
        if not path.exists() or path.stat().st_size < 10000:
            logger.info(f"Model {name} missing or incomplete. Downloading from {url}...")
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with requests.get(url, stream=True, timeout=90) as r:
                    r.raise_for_status()
                    temp_path = path.with_suffix(".tmp")
                    with open(temp_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                f.write(chunk)
                    if temp_path.exists():
                        if path.exists():
                            path.unlink()
                        temp_path.rename(path)
                logger.info(f"Successfully downloaded {name} ({path.stat().st_size} bytes)")
            except Exception as e:
                logger.error(f"Failed to download {name}: {e}")
                success = False
        else:
            logger.info(f"Found model {name} at {path}")
    return success
