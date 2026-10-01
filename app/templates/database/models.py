from datetime import datetime
from typing import Dict, List, Optional, Any
from app.database.db import get_db_connection

class StudentDB:
    @staticmethod
    def create_student(data: Dict[str, Any]) -> int:
        conn = get_db_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO students (student_id, name, email, phone, department, year_semester, gender, face_samples_count, primary_photo_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["student_id"].strip().upper(),
                    data["name"].strip(),
                    data.get("email", "").strip(),
                    data.get("phone", "").strip(),
                    data["department"].strip(),
                    data.get("year_semester", "").strip(),
                    data.get("gender", "Other"),
                    data.get("face_samples_count", 0),
                    data.get("primary_photo_path", "")
                ))
                return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def get_student_by_id(student_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id.strip().upper(),))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_all_students(search: Optional[str] = None, department: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM students WHERE is_active = 1"
            params = []

            if search:
                query += " AND (student_id LIKE ? OR name LIKE ? OR email LIKE ?)"
                wildcard = f"%{search}%"
                params.extend([wildcard, wildcard, wildcard])

            if department and department != "All":
                query += " AND department = ?"
                params.append(department)

            query += " ORDER BY name ASC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def update_student(student_id: str, data: Dict[str, Any]) -> bool:
        conn = get_db_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE students
                    SET name = ?, email = ?, phone = ?, department = ?, year_semester = ?, gender = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE student_id = ?
                """, (
                    data["name"].strip(),
                    data.get("email", "").strip(),
                    data.get("phone", "").strip(),
                    data["department"].strip(),
                    data.get("year_semester", "").strip(),
                    data.get("gender", "Other"),
                    student_id.strip().upper()
                ))
                return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def update_face_count(student_id: str, count: int, primary_photo_path: Optional[str] = None) -> bool:
        conn = get_db_connection()
        try:
            with conn:
                cursor = conn.cursor()
                if primary_photo_path:
                    cursor.execute("""
                        UPDATE students
                        SET face_samples_count = ?, primary_photo_path = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE student_id = ?
                    """, (count, primary_photo_path, student_id.strip().upper()))
                else:
                    cursor.execute("""
                        UPDATE students
                        SET face_samples_count = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE student_id = ?
                    """, (count, student_id.strip().upper()))
                return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def delete_student(student_id: str) -> bool:
        conn = get_db_connection()
        try:
            with conn:
                cursor = conn.cursor()
                # Remove attendance records for student
                cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id.strip().upper(),))
                cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id.strip().upper(),))
                return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def count_students() -> int:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM students WHERE is_active = 1")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    @staticmethod
    def get_all_departments() -> List[str]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT department FROM students WHERE is_active = 1 ORDER BY department")
            return [row[0] for row in cursor.fetchall() if row[0]]
        finally:
            conn.close()


class AttendanceDB:
    @staticmethod
    def record_attendance(
        student_id: str,
        student_name: str,
        department: str,
        date_str: str,
        time_str: str,
        confidence: float = 1.0,
        status: str = "Present",
        method: str = "AI Face Recognition",
        notes: str = ""
    ) -> Optional[int]:
        """Inserts an attendance record. Returns record ID if inserted, None if duplicate."""
        conn = get_db_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO attendance (student_id, student_name, department, date, time, confidence, status, method, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    student_id.strip().upper(),
                    student_name.strip(),
                    department.strip(),
                    date_str,
                    time_str,
                    round(float(confidence), 4),
                    status,
                    method,
                    notes
                ))
                return cursor.lastrowid
        except Exception as e:
            # Duplicate entry on (student_id, date) or integrity error
            return None
        finally:
            conn.close()

    @staticmethod
    def has_attended_today(student_id: str, date_str: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM attendance WHERE student_id = ? AND date = ?
            """, (student_id.strip().upper(), date_str))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_attendance_records(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        department: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM attendance WHERE 1=1"
            params = []

            if date:
                query += " AND date = ?"
                params.append(date)
            else:
                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date)

            if department and department != "All":
                query += " AND department = ?"
                params.append(department)

            if status and status != "All":
                query += " AND status = ?"
                params.append(status)

            if search:
                query += " AND (student_id LIKE ? OR student_name LIKE ?)"
                wildcard = f"%{search}%"
                params.extend([wildcard, wildcard])

            query += " ORDER BY date DESC, time DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def delete_record(record_id: int) -> bool:
        conn = get_db_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM attendance WHERE id = ?", (record_id,))
                return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def get_dashboard_stats(today_date: str) -> Dict[str, Any]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Total registered
            cursor.execute("SELECT COUNT(*) FROM students WHERE is_active = 1")
            total_students = cursor.fetchone()[0]

            # Today present / late
            cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today_date,))
            today_present = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Late'", (today_date,))
            today_late = cursor.fetchone()[0]

            # Today on-time
            today_on_time = max(0, today_present - today_late)

            # Absent
            today_absent = max(0, total_students - today_present)

            # Percentage
            attendance_rate = round((today_present / total_students * 100), 1) if total_students > 0 else 0.0

            # Last 7 days attendance trend
            cursor.execute("""
                SELECT date, COUNT(*) as count 
                FROM attendance 
                GROUP BY date 
                ORDER BY date DESC 
                LIMIT 7
            """)
            trend_rows = cursor.fetchall()
            trend = [{"date": r["date"], "count": r["count"]} for r in reversed(trend_rows)]

            # Department breakdown for today
            cursor.execute("""
                SELECT department, COUNT(*) as count
                FROM attendance
                WHERE date = ?
                GROUP BY department
            """, (today_date,))
            dept_breakdown = [{"department": r["department"], "count": r["count"]} for r in cursor.fetchall()]

            return {
                "total_students": total_students,
                "today_present": today_present,
                "today_late": today_late,
                "today_on_time": today_on_time,
                "today_absent": today_absent,
                "attendance_rate": attendance_rate,
                "trend": trend,
                "dept_breakdown": dept_breakdown
            }
        finally:
            conn.close()


class SettingsDB:
    @staticmethod
    def get_all_settings() -> Dict[str, str]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM system_settings")
            return {row["key"]: row["value"] for row in cursor.fetchall()}
        finally:
            conn.close()

    @staticmethod
    def get_setting(key: str, default: str = "") -> str:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default
        finally:
            conn.close()

    @staticmethod
    def update_setting(key: str, value: str) -> None:
        conn = get_db_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO system_settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """, (key, str(value)))
        finally:
            conn.close()
