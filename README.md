# AI Attendance System 🎓📸

An enterprise-grade, real-time AI-powered facial recognition attendance system built with **FastAPI**, **OpenCV Deep Learning (YuNet + SFace)**, and a modern responsive web frontend.

---

## 🌟 Key Features

- **Automated AI Face Detection & Recognition**:
  - Primary Neural Engine: **OpenCV YuNet** (high-accuracy deep CNN face detector) and **SFace** (128-dimensional deep feature embeddings).
  - High performance (60+ FPS processing on standard CPU, sub-millisecond vector matching).
  - Automatic fallback to OpenCV Haar Cascades and LBPH face recognition.

- **Real-Time Webcam Attendance Scanner**:
  - Live HUD targeting reticle with smooth bounding box tracking.
  - Multi-face detection with real-time identification.
  - Web Audio API synthesized audio chimes for instant auditory confirmation (zero external MP3 files needed).
  - Dual Mode: Browser WebRTC camera mode (works on any device) or Server OpenCV webcam stream.

- **Strict Duplicate Attendance Prevention**:
  - Automatically records current date and time.
  - Enforces database-level constraint `UNIQUE(student_id, date)` preventing duplicate attendance on the same day.
  - In-scanner smart cooldown preventing repeated alerts for students standing in front of the camera.

- **Late Arrival Evaluation**:
  - Configurable daily cutoff time (e.g., `09:30 AM`).
  - Automatically tags arrival as **Present** or **Late**.

- **Interactive Student Face Enrollment**:
  - Multi-sample enrollment (1 to 5 face shots: front, slight tilt) for maximum accuracy.
  - Live oval alignment guide in camera preview.
  - Drag-and-drop / file upload support for student profile photos.

- **Student Management Directory**:
  - Complete database of registered students with photo avatars.
  - Instant live search by Roll Number, Name, or Email.
  - Department and course filtering.
  - Edit student profile, re-enroll face samples, or delete student records.

- **Attendance History & Analytics**:
  - Date presets: Today, Yesterday, Last 7 Days, This Month, or Custom Date Range.
  - Status and Department filters.
  - One-click **Export to CSV** (with UTF-8 BOM for Microsoft Excel).
  - One-click **Export to Excel (.xlsx)** with auto-formatted column widths, header themes, and color-coded status badges.
  - Manual attendance override modal with administrator audit notes.

- **Executive Admin Dashboard**:
  - Real-time KPI summary cards (Total Students, Present Today, Late Today, Attendance Rate %).
  - Interactive 7-Day Attendance Trend chart (Chart.js).
  - Department-wise attendance breakdown doughnut chart.
  - Live activity feed showing check-ins as they happen.

- **Modern Responsive Dark/Light UI**:
  - Custom glassmorphism, responsive desktop sidebar, collapsible mobile menu.
  - Live ticking digital clock with date synchronization.

---

## 📂 Modular Architecture

```
AI_Attendance_System/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application setup & page routes
│   ├── config.py                   # Paths, thresholds, model settings, constants
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py                   # SQLite connection with WAL mode & table schemas
│   │   └── models.py               # Student, Attendance, and Settings data access objects
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── model_manager.py        # Model downloading & verification
│   │   └── face_engine.py          # YuNet & SFace deep learning recognition engine
│   ├── services/
│   │   ├── __init__.py
│   │   ├── student_service.py      # Student CRUD & face enrollment handling
│   │   ├── attendance_service.py   # Live frame processing, duplicate prevention & stats
│   │   ├── export_service.py       # CSV and formatted Excel (.xlsx) generators
│   │   └── camera_service.py       # Local OpenCV webcam capture & MJPEG streaming
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_students.py      # /api/students endpoints
│   │   ├── routes_attendance.py    # /api/attendance endpoints
│   │   ├── routes_export.py        # /api/export/csv and /api/export/excel endpoints
│   │   └── routes_system.py        # /api/system/settings and status endpoints
│   ├── static/
│   │   ├── css/styles.css          # Responsive dark/light theme stylesheet
│   │   └── js/
│   │       ├── main.js             # Clock, theme, modals, Web Audio chimes
│   │       ├── dashboard.js        # Analytics charts & live feed updates
│   │       ├── scanner.js          # Live webcam scanner & HUD overlay renderer
│   │       ├── register.js         # Student registration & face capture logic
│   │       ├── students.js         # Student directory search & management
│   │       └── attendance.js       # Historical records, filters & exports
│   └── templates/
│       ├── base.html               # Master layout with sidebar & topbar
│       ├── dashboard.html          # Overview dashboard
│       ├── scanner.html            # Real-time attendance kiosk
│       ├── register.html           # Student registration & face enrollment
│       ├── students.html           # Student directory & management
│       ├── attendance.html         # Attendance logs & reports
│       └── settings.html           # Settings & AI diagnostics
├── data/
│   ├── attendance.db               # SQLite database
│   ├── faces/                      # Stored student face sample crops
│   ├── models/                     # YuNet and SFace ONNX models
│   └── exports/                    # Generated report files
├── venv/                           # Python virtual environment
├── run.py                          # Application entry point
├── start.bat                       # One-click Windows batch launcher
├── requirements.txt                # Pinned dependencies
└── README.md                       # Documentation
```

---

## 🚀 Quick Start Guide (Windows)

### 1. Prerequisites
- Python 3.10+ or Python 3.11 installed on your system.
- Webcam (built-in laptop camera or external USB webcam).

### 2. Automatic Launch
Simply double-click the included `start.bat` file in the project folder.

### 3. Manual Launch via Terminal
Activate the virtual environment and run `run.py`:

```powershell
# Activate the virtual environment
.\venv\Scripts\activate

# Run the system
python run.py
```

The system will automatically initialize the database, verify the deep learning models, start the web server at `http://127.0.0.1:8000`, and launch your web browser.

---

## 📖 How to Use

### 1. Enrolling a Student
1. Navigate to **Enroll Student** (`/register`) from the sidebar.
2. Fill in the student's details (Student ID / Roll No, Full Name, Department, Year/Semester, Email, Phone).
3. Click **Start Camera** and position the student's face within the oval guide.
4. Click **Capture Sample** (or click **Auto 3-Shot** for 3 quick multi-angle captures).
5. Click **Register & Enroll Face**. The AI engine aligns the face, extracts 128-dimensional neural embeddings, and saves the student to the database.

### 2. Taking Live Attendance
1. Navigate to **Live Scanner** (`/scanner`).
2. Click **Start Camera**.
3. When an enrolled student approaches the camera:
   - The HUD draws a green bracket around their face.
   - A pleasant chime plays.
   - Attendance is instantly marked in the database.
   - The student's photo and details appear on the Live Recognition card.
4. If the student stays in front of the camera or returns later on the same day:
   - The system recognizes them, displays *"Already Checked In"*, and prevents duplicate entries.

### 3. Reviewing Logs & Exporting Reports
1. Navigate to **Attendance Records** (`/attendance`).
2. Filter by date presets (Today, Last 7 Days, Month) or custom date range.
3. Click **CSV Export** to download a CSV spreadsheet.
4. Click **Excel (.xlsx)** to download a styled Microsoft Excel workbook with highlighted status columns and summary metrics.

---

## 🛠️ REST API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/attendance/recognize-frame` | `POST` | Detects, recognizes faces in base64 frame, and marks attendance |
| `/api/attendance/mark-manual` | `POST` | Manually mark student attendance with admin notes |
| `/api/attendance/history` | `GET` | Get filtered attendance logs |
| `/api/attendance/stats` | `GET` | Get dashboard KPIs, 7-day trends, and department breakdowns |
| `/api/attendance/{id}` | `DELETE` | Delete an attendance record |
| `/api/students/register` | `POST` | Register a new student and enroll face samples |
| `/api/students` | `GET` | List all students with search and department filtering |
| `/api/students/{id}` | `GET` / `PUT` / `DELETE` | View, update, or delete student |
| `/api/students/{id}/re-enroll` | `POST` | Re-enroll new face photos for an existing student |
| `/api/export/csv` | `GET` | Export attendance report in CSV format |
| `/api/export/excel` | `GET` | Export formatted Excel `.xlsx` workbook |
| `/api/system/settings` | `GET` / `POST` | Read or update late arrival cutoff, threshold, cooldown |
| `/api/system/status` | `GET` | AI engine diagnostics and model status |

---

## 🔒 Security & Data Integrity
- Database uses **SQLite WAL mode** for concurrent multi-threaded read/write safety.
- Face crops are stored locally in `data/faces/` and never transmitted to external clouds.
- Database enforces `UNIQUE(student_id, date)` preventing any duplicate attendance.

---

## 📄 License
This project is licensed under the MIT License.
