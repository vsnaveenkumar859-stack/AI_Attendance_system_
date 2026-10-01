// ==========================================================================
// AI Attendance System - Student Directory Management Script
// ==========================================================================

let studentsCache = [];
let reenrollImages = [];
let currentReenrollStudentId = null;

const searchInput = document.getElementById("student-search-input");
const deptFilter = document.getElementById("student-dept-filter");
const tableBody = document.getElementById("students-table-body");
const countBadge = document.getElementById("students-count-badge");

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

async function loadStudents() {
    const search = searchInput.value.trim();
    const dept = deptFilter.value;

    let url = "/api/students?";
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (dept && dept !== "All") params.append("department", dept);
    url += params.toString();

    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            studentsCache = data.students || [];
            renderStudentsTable(studentsCache);
        }
    } catch (e) {
        console.error("Failed to load students:", e);
        tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #EF4444; padding: 2rem;">Failed to load students from server.</td></tr>`;
    }
}

function renderStudentsTable(students) {
    countBadge.textContent = `${students.length} Student${students.length === 1 ? '' : 's'}`;

    if (!students || students.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 3rem; color: var(--text-subtle);">
                    No students found matching your criteria.
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = students.map(s => {
        const photoUrl = s.primary_photo_path || `/static/faces/${s.student_id}/sample_1.jpg`;
        const dateStr = s.created_at ? s.created_at.split(' ')[0] : '---';

        return `
            <tr>
                <td>
                    <img src="${photoUrl}" class="avatar" alt="${s.name}" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'40\\' height=\\'40\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'%2364748B\\' stroke-width=\\'1.5\\'><path d=\\'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2\\'/><circle cx=\\'12\\' cy=\\'7\\' r=\\'4\\'/></svg>'" />
                </td>
                <td>
                    <span style="font-family: monospace; font-weight: 700; color: #60A5FA;">${s.student_id}</span>
                </td>
                <td style="font-weight: 600;">
                    ${s.name}
                    ${s.email ? `<div style="font-size: 0.75rem; color: var(--text-subtle);">${s.email}</div>` : ''}
                </td>
                <td><span class="badge badge-info">${s.department}</span></td>
                <td>${s.year_semester || '---'}</td>
                <td>
                    <span class="badge badge-success" title="Enrolled sample images">
                        ${s.face_samples_count || 1} Samples
                    </span>
                </td>
                <td style="color: var(--text-muted); font-size: 0.8rem;">${dateStr}</td>
                <td style="text-align: right;">
                    <div style="display: inline-flex; gap: 0.35rem;">
                        <button class="btn btn-secondary btn-sm" onclick="openEditModal('${s.student_id}')" title="Edit Student">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="openReenrollModal('${s.student_id}', '${s.name}')" title="Re-enroll Face">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                                <circle cx="12" cy="13" r="4"></circle>
                            </svg>
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="deleteStudent('${s.student_id}', '${s.name}')" title="Delete Student">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Edit Modal Functions
function openEditModal(studentId) {
    const s = studentsCache.find(x => x.student_id === studentId);
    if (!s) return;

    document.getElementById("edit-student-id-hidden").value = s.student_id;
    document.getElementById("edit-student-id-display").value = s.student_id;
    document.getElementById("edit-name").value = s.name;
    document.getElementById("edit-dept").value = s.department;
    document.getElementById("edit-year").value = s.year_semester || "";
    document.getElementById("edit-email").value = s.email || "";
    document.getElementById("edit-phone").value = s.phone || "";
    document.getElementById("edit-gender").value = s.gender || "Other";

    openModal("edit-student-modal");
}

async function saveEditStudent() {
    const studentId = document.getElementById("edit-student-id-hidden").value;
    const payload = {
        name: document.getElementById("edit-name").value.trim(),
        department: document.getElementById("edit-dept").value.trim(),
        year_semester: document.getElementById("edit-year").value.trim(),
        email: document.getElementById("edit-email").value.trim(),
        phone: document.getElementById("edit-phone").value.trim(),
        gender: document.getElementById("edit-gender").value
    };

    if (!payload.name || !payload.department) {
        showToast("Name and Department are required.", "warning");
        return;
    }

    try {
        const res = await fetch(`/api/students/${studentId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast("Student details updated successfully!", "success");
            closeModal("edit-student-modal");
            loadStudents();
        } else {
            showToast(`Update error: ${data.detail || "Failed"}`, "danger");
        }
    } catch (e) {
        showToast("Server error during update.", "danger");
    }
}

// Re-enroll Face Modal Functions
function openReenrollModal(studentId, name) {
    currentReenrollStudentId = studentId;
    reenrollImages = [];
    document.getElementById("reenroll-student-name").textContent = `${name} (${studentId})`;
    document.getElementById("reenroll-samples-preview").innerHTML = '<span style="color: var(--text-subtle); font-size: 0.8rem;">No new photos selected yet.</span>';
    document.getElementById("btn-submit-reenroll").disabled = true;
    openModal("reenroll-modal");
}

function handleReenrollFile(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    files.forEach(f => {
        if (reenrollImages.length >= 5) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            reenrollImages.push(event.target.result);
            renderReenrollPreview();
        };
        reader.readAsDataURL(f);
    });
}

function renderReenrollPreview() {
    const container = document.getElementById("reenroll-samples-preview");
    const submitBtn = document.getElementById("btn-submit-reenroll");

    if (reenrollImages.length === 0) {
        container.innerHTML = '<span style="color: var(--text-subtle); font-size: 0.8rem;">No new photos selected yet.</span>';
        submitBtn.disabled = true;
        return;
    }

    container.innerHTML = reenrollImages.map((b64, idx) => `
        <div style="position: relative; width: 64px; height: 64px; border-radius: var(--radius-sm); overflow: hidden; border: 2px solid #3B82F6;">
            <img src="${b64}" style="width: 100%; height: 100%; object-fit: cover;" />
        </div>
    `).join('');
    submitBtn.disabled = false;
}

async function submitReenroll() {
    if (!currentReenrollStudentId || reenrollImages.length === 0) return;

    const submitBtn = document.getElementById("btn-submit-reenroll");
    submitBtn.disabled = true;
    submitBtn.textContent = "Processing...";

    try {
        const res = await fetch(`/api/students/${currentReenrollStudentId}/re-enroll`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ images: reenrollImages })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            playSound('success');
            showToast(data.message, "success", 4000);
            closeModal("reenroll-modal");
            loadStudents();
        } else {
            showToast(`Re-enrollment error: ${data.detail || data.message}`, "danger", 5000);
        }
    } catch (e) {
        showToast("Server communication error.", "danger");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Confirm & Update Model";
    }
}

// Delete Student
async function deleteStudent(studentId, name) {
    const confirmed = confirm(`Are you sure you want to permanently delete student "${name}" (${studentId}) and all their face biometric data and attendance records?`);
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/students/${studentId}`, { method: "DELETE" });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast(data.message, "success");
            loadStudents();
        } else {
            showToast(`Delete failed: ${data.detail || "Error"}`, "danger");
        }
    } catch (e) {
        showToast("Error communicating with server.", "danger");
    }
}

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
    loadDepartments();
    loadStudents();

    let searchTimeout = null;
    searchInput.addEventListener("input", () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(loadStudents, 250);
    });

    deptFilter.addEventListener("change", loadStudents);

    document.getElementById("btn-save-edit-student").addEventListener("click", saveEditStudent);
    document.getElementById("reenroll-file-input").addEventListener("change", handleReenrollFile);
    document.getElementById("btn-submit-reenroll").addEventListener("click", submitReenroll);
});
