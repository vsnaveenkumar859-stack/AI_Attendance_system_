import os
import sys
import webbrowser
import threading
import time
import uvicorn

from app.config import HOST, PORT, APP_NAME, APP_VERSION
from app.database import init_db
from app.ai.model_manager import ensure_models

def open_browser(url: str):
    """Wait 1.5 seconds for Uvicorn server to bind and open default web browser."""
    time.sleep(1.5)
    try:
        webbrowser.open(url)
    except Exception:
        pass

def main():
    print("=" * 65)
    print(f"   {APP_NAME} v{APP_VERSION}")
    print("=" * 65)
    print("[*] Initializing Database Schema...")
    init_db()

    print("[*] Checking AI Deep Learning Models (YuNet + SFace)...")
    ensure_models()

    server_url = f"http://{HOST}:{PORT}"
    print(f"[*] Starting Application Server at: {server_url}")
    print(f"[*] Dashboard:       {server_url}/")
    print(f"[*] Live Scanner:    {server_url}/scanner")
    print(f"[*] Enroll Student:  {server_url}/register")
    print(f"[*] Press CTRL+C to stop the server.")
    print("=" * 65)

    # Automatically launch default browser in separate thread
    threading.Thread(target=open_browser, args=(server_url,), daemon=True).start()

    # Run Uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False, log_level="info")

if __name__ == "__main__":
    main()
