// ==========================================================================
// AI Attendance System - Attendance History, Search, Filter & Export Script
// ==========================================================================

let activeDatePreset = "all";

const searchInput = document.getElementById("att-search-input");
const deptFilter = document.getElementById("att-dept-filter");
const statusFilter = document.getElementById("att-status-filter");
const startDateInput = document.getElementById("att-start-date");
const endDateInput = document.getElementById("att-end-date");
const tableBody = document.getElementById("attendance-table-body");

const totalBadge = document.getElementById("badge-total-records");
const presentBadge = document.getElementById("badge-total-present");
const lateBadge = document.getElementById("badge-total-late");

// 1. Department List
async function loadDepartments() {
    try {
        const res = await fetch("/api/students/departments/list");
        const data = await res.json();
        if (data.success && data.departments) {
            deptFilter.innerHTML = '<option value="All">All Departments</option>' + 
                data.departments.map(d => `<option value="${d}">${d}</option>`).join('');
        }
    } catch (e) {
        console.warn("Could not load departments:", e);
    }
}

// 2. Query URL Builder
function buildQueryUrl(baseEndpoint) {
    const params = new URLSearchParams();
    const search = searchInput.value.trim();
    const dept = deptFilter.value;
    const status = statusFilter.value;
    const start = startDateInput.value;
    const end = endDateInput.value;

    if (search) params.append("search", search);
    if (dept && dept !== "All") params.append("department", dept);
    if (status && status !== "All") params.append("status", status);

    if (start && end && start === end) {
        params.append("date", start);
    } else {
        if (start) params.append("start_date", start);
        if (end) params.append("end_date", end);
    }

    const qs = params.toString();
    return qs ? `${baseEndpoint}?${qs}` : baseEndpoint;
}

// 3. Load & Render Attendance History
async function loadAttendanceRecords() {
    const url = buildQueryUrl("/api/attendance/history");
    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            renderAttendanceTable(data.records || []);
        }
    } catch (e) {
        console.error("Failed to load records:", e);
        tableBody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: #EF4444; padding: 2rem;">Error loading attendance records.</td></tr>`;
    }
}

function renderAttendanceTable(records) {
    const total = records.length;
    const present = records.filter(r => r.status === 'Present').length;
    const late = records.filter(r => r.status === 'Late').length;

    totalBadge.textContent = `${total} Records`;
    presentBadge.textContent = `${present} Present`;
    lateBadge.textContent = `${late} Late`;

    if (!records || records.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 3rem; color: var(--text-subtle);">
                    No attendance records found for the selected criteria.
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = records.map(r => {
        const isPresent = r.status === 'Present';
        const statusBadge = isPresent
            ? `<span class="badge badge-present">Present</span>`
            : `<span class="badge badge-late">Late</span>`;
        const conf = (parseFloat(r.confidence || 1.0) * 100).toFixed(0);

        return `
            <tr>
                <td style="font-family: monospace; font-weight: 500;">${r.date}</td>
                <td style="font-family: monospace; font-weight: 600; color: #60A5FA;">${r.time}</td>
                <td><span style="font-family: monospace; font-weight: 700;">${r.student_id}</span></td>
                <td style="font-weight: 600;">${r.student_name}</td>
                <td><span class="badge badge-info">${r.department}</span></td>
                <td>${statusBadge}</td>
                <td style="font-weight: 600;">${conf}%</td>
                <td style="color: var(--text-muted); font-size: 0.8rem;">${r.method || 'AI Face'}</td>
                <td style="color: var(--text-subtle); font-size: 0.8rem;">${r.notes || '---'}</td>
                <td style="text-align: right;">
                    <button class="btn btn-secondary btn-sm" onclick="deleteAttendanceRecord(${r.id})" title="Delete Record">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// 4. Date Presets Handler
function applyDatePreset(preset) {
    activeDatePreset = preset;
    document.querySelectorAll(".date-preset-btn").forEach(b => {
        b.classList.toggle("active", b.getAttribute("data-preset") === preset);
    });

    const now = new Date();
    const toYMD = (d) => d.toISOString().split('T')[0];

    if (preset === "all") {
        startDateInput.value = "";
        endDateInput.value = "";
    } else if (preset === "today") {
        const todayStr = toYMD(now);
        startDateInput.value = todayStr;
        endDateInput.value = todayStr;
    } else if (preset === "yesterday") {
        const y = new Date();
        y.setDate(y.getDate() - 1);
        const yStr = toYMD(y);
        startDateInput.value = yStr;
        endDateInput.value = yStr;
    } else if (preset === "week") {
        const past = new Date();
        past.setDate(past.getDate() - 6);
        startDateInput.value = toYMD(past);
        endDateInput.value = toYMD(now);
    } else if (preset === "month") {
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        startDateInput.value = toYMD(firstDay);
        endDateInput.value = toYMD(now);
    }

    loadAttendanceRecords();
}

// 5. Delete Record
async function deleteAttendanceRecord(id) {
    if (!confirm("Are you sure you want to delete this attendance record?")) return;
    try {
        const res = await fetch(`/api/attendance/${id}`, { method: "DELETE" });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast("Record deleted", "info");
            loadAttendanceRecords();
        } else {
            showToast("Failed to delete record.", "danger");
        }
    } catch (e) {
        showToast("Error contacting server.", "danger");
    }
}

// 6. Manual Entry Modal
function openManualModal() {
    const now = new Date();
    document.getElementById("manual-student-id").value = "";
    document.getElementById("manual-date").value = now.toISOString().split('T')[0];
    document.getElementById("manual-time").value = now.toTimeString().split(' ')[0];
    document.getElementById("manual-status").value = "Present";
    document.getElementById("manual-notes").value = "Manual Entry by Admin";
    openModal("manual-att-modal");
}

async function submitManualAttendance() {
    const studentId = document.getElementById("manual-student-id").value.trim();
    const date = document.getElementById("manual-date").value;
    const time = document.getElementById("manual-time").value;
    const status = document.getElementById("manual-status").value;
    const notes = document.getElementById("manual-notes").value.trim();

    if (!studentId || !date || !time) {
        showToast("Please fill in Student ID, Date, and Time.", "warning");
        return;
    }

    try {
        const res = await fetch("/api/attendance/mark-manual", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id: studentId,
                date: date,
                time: time,
                status: status,
                notes: notes
            })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            playSound('success');
            showToast(`Attendance recorded manually for ${data.student_name}!`, "success");
            closeModal("manual-att-modal");
            loadAttendanceRecords();
        } else {
            showToast(`Manual record failed: ${data.detail || data.message || "Failed"}`, "danger");
        }
    } catch (e) {
        showToast("Network error.", "danger");
    }
}

// 7. Export Handlers
function triggerExport(type) {
    const endpoint = type === 'csv' ? '/api/export/csv' : '/api/export/excel';
    const url = buildQueryUrl(endpoint);
    window.location.href = url;
    showToast(`Downloading ${type.toUpperCase()} report...`, "info", 3000);
}

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
    loadDepartments();
    loadAttendanceRecords();

    let searchTimeout = null;
    searchInput.addEventListener("input", () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(loadAttendanceRecords, 250);
    });

    deptFilter.addEventListener("change", loadAttendanceRecords);
    statusFilter.addEventListener("change", loadAttendanceRecords);
    startDateInput.addEventListener("change", loadAttendanceRecords);
    endDateInput.addEventListener("change", loadAttendanceRecords);

    document.querySelectorAll(".date-preset-btn").forEach(btn => {
        btn.addEventListener("click", () => applyDatePreset(btn.getAttribute("data-preset")));
    });

    document.getElementById("btn-export-csv").addEventListener("click", () => triggerExport("csv"));
    document.getElementById("btn-export-excel").addEventListener("click", () => triggerExport("excel"));

    document.getElementById("btn-open-manual-modal").addEventListener("click", openManualModal);
    document.getElementById("btn-submit-manual-att").addEventListener("click", submitManualAttendance);
});
