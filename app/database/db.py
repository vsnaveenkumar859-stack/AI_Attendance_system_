import sqlite3
from typing import Generator
from app.config import DB_PATH

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured with Row factory and WAL mode."""
    conn = sqlite3.connect(str(DB_PATH), timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db() -> None:
    """Initializes tables and indexes if they do not exist."""
    conn = get_db_connection()
    try:
        with conn:
            # 1. Students Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    department TEXT NOT NULL,
                    year_semester TEXT,
                    gender TEXT,
                    face_samples_count INTEGER DEFAULT 0,
                    primary_photo_path TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Attendance Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    student_name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Present',
                    confidence REAL DEFAULT 1.0,
                    method TEXT DEFAULT 'AI Face Recognition',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(student_id, date) ON CONFLICT FAIL
                );
            """)

            # 3. Settings Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            # Indexes for ultra-fast search & query
            conn.execute("CREATE INDEX IF NOT EXISTS idx_students_id ON students(student_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_dept ON attendance(department);")

            # Seed default system settings if not already present
            default_settings = [
                ("late_cutoff_time", "09:30"),
                ("cosine_threshold", "0.45"),
                ("duplicate_cooldown", "8"),
                ("system_title", "AI Attendance System"),
                ("active_camera_index", "0")
            ]
            for key, val in default_settings:
                conn.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?);", (key, val))
    finally:
        conn.close()
