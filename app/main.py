import flet as ft
import cv2
import base64
import datetime
import threading
import time

def main(page: ft.Page):
    page.title = "AI Attendance System"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window.width = 900
    page.window.height = 700

    # UI Elements
    title = ft.Text("AI Attendance System", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200)
    img_control = ft.Image(src="", width=480, height=360, fit="contain")
    
    # Attendance Table
    attendance_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Name")),
            ft.DataColumn(ft.Text("Time")),
            ft.DataColumn(ft.Text("Status")),
        ],
        rows=[]
    )

    status_text = ft.Text("Camera Active", size=16, color=ft.Colors.GREEN_400)

    def mark_attendance(e):
        current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
        attendance_table.rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text("Student / User")),
                    ft.DataCell(ft.Text(current_time)),
                    ft.DataCell(ft.Text("Present", color=ft.Colors.GREEN_300)),
                ]
            )
        )
        status_text.value = f"Attendance Marked at {current_time}!"
        page.update()

    mark_btn = ft.Button(
        "Mark Attendance", 
        icon=ft.Icons.CAMERA_ALT, 
        on_click=mark_attendance
    )

    # UI Layout
    page.add(
        ft.Column([
            title,
            ft.Divider(),
            ft.Row([
                ft.Column([
                    ft.Text("Live Camera Feed", size=18, weight=ft.FontWeight.W_500),
                    img_control,
                    mark_btn,
                    status_text
                ], alignment=ft.MainAxisAlignment.START),
                ft.VerticalDivider(),
                ft.Column([
                    ft.Text("Today's Attendance Log", size=18, weight=ft.FontWeight.W_500),
                    attendance_table
                ], expand=True)
            ], expand=True)
        ])
    )

    # Background Camera Loop Function
    def update_camera():
        cap = cv2.VideoCapture(0)
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.03)
                continue
            
            try:
                _, buffer = cv2.imencode('.jpg', frame)
                base64_img = base64.b64encode(buffer).decode('utf-8')
                img_control.src_base64 = base64_img
                page.update()
            except Exception:
                break
            time.sleep(0.03)
        
        cap.release()

    # Start Camera in Threading
    threading.Thread(target=update_camera, daemon=True).start()

ft.run(main)