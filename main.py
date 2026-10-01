import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import STATIC_DIR, TEMPLATES_DIR, FACES_DIR, APP_NAME, APP_VERSION
from app.database import init_db
from app.ai.face_engine import face_engine
from app.services.camera_service import camera_service
from app.api import api_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_attendance")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and load face embeddings
    logger.info("Starting AI Attendance System...")
    init_db()
    face_engine.reload_known_faces()
    yield
    # Shutdown: Release camera
    logger.info("Shutting down AI Attendance System...")
    camera_service.stop_camera()

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Directories
app.mount("/static/faces", StaticFiles(directory=str(FACES_DIR)), name="faces")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API Router
app.include_router(api_router)

# ----------------- Web UI Page Routes -----------------

@app.get("/", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "active_page": "dashboard",
        "app_name": APP_NAME,
        "app_version": APP_VERSION
    })

@app.get("/scanner", response_class=HTMLResponse)
async def page_scanner(request: Request):
    return templates.TemplateResponse(request=request, name="scanner.html", context={
        "active_page": "scanner",
        "app_name": APP_NAME,
        "app_version": APP_VERSION
    })

@app.get("/register", response_class=HTMLResponse)
async def page_register(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={
        "active_page": "register",
        "app_name": APP_NAME,
        "app_version": APP_VERSION
    })

@app.get("/students", response_class=HTMLResponse)
async def page_students(request: Request):
    return templates.TemplateResponse(request=request, name="students.html", context={
        "active_page": "students",
        "app_name": APP_NAME,
        "app_version": APP_VERSION
    })

@app.get("/attendance", response_class=HTMLResponse)
async def page_attendance(request: Request):
    return templates.TemplateResponse(request=request, name="attendance.html", context={
        "active_page": "attendance",
        "app_name": APP_NAME,
        "app_version": APP_VERSION
    })

@app.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    return templates.TemplateResponse(request=request, name="settings.html", context={
        "active_page": "settings",
        "app_name": APP_NAME,
        "app_version": APP_VERSION
    })

# Exception Handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"error": "Not Found"})
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"error": "Page not found"}, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error(f"Internal server error: {exc}")
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=500, content={"error": "Internal Server Error", "details": str(exc)})
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"error": "Internal server error"}, status_code=500)
