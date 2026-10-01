// ==========================================================================
// AI Attendance System - Student Registration & Face Enrollment Logic
// ==========================================================================

let enrollStream = null;
let capturedSamples = []; // Array of base64 image strings

const enrollVideo = document.getElementById("enroll-video");
const placeholder = document.getElementById("enroll-camera-placeholder");
const btnStartCam = document.getElementById("btn-start-enroll-cam");
const btnSnap = document.getElementById("btn-snap-photo");
const btnAuto = document.getElementById("btn-auto-capture");
const fileUpload = document.getElementById("file-photo-upload");
const samplesContainer = document.getElementById("samples-container");
const counterBadge = document.getElementById("enroll-sample-counter");
const submitBtn = document.getElementById("btn-submit-enroll");
const enrollForm = document.getElementById("enroll-form");

// 1. Start Camera
async function startEnrollCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: false
        });
        enrollStream = stream;
        enrollVideo.srcObject = stream;
        await enrollVideo.play();

        enrollVideo.style.display = "block";
        placeholder.style.display = "none";
        btnSnap.disabled = false;
        btnAuto.disabled = false;
        showToast("Camera started. Look directly inside the oval guide.", "info", 2500);
    } catch (e) {
        console.error("Camera access failed:", e);
        showToast("Could not access camera. Please allow permissions or upload a photo.", "danger", 4000);
    }
}

// 2. Capture a Single Snapshot
function captureSnapshot() {
    if (!enrollVideo.videoWidth) {
        showToast("Camera is not ready yet.", "warning", 2000);
        return;
    }

    if (capturedSamples.length >= 5) {
        showToast("Maximum 5 face samples allowed.", "info", 2000);
        return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = enrollVideo.videoWidth;
    canvas.height = enrollVideo.videoHeight;
    const ctx = canvas.getContext("2d");

    // Mirror to match preview
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(enrollVideo, 0, 0, canvas.width, canvas.height);

    const b64 = canvas.toDataURL("image/jpeg", 0.9);
    addSample(b64);
    playSound('success');
}

// 3. Auto 3-Shot Sequence
async function startAutoCapture() {
    btnAuto.disabled = true;
    btnSnap.disabled = true;

    for (let i = 1; i <= 3; i++) {
        if (capturedSamples.length >= 5) break;
        showToast(`Capturing sample ${i} of 3 in 1 second... Hold still!`, "info", 1000);
        await new Promise(r => setTimeout(r, 1000));
        captureSnapshot();
    }

    btnAuto.disabled = false;
    btnSnap.disabled = false;
    showToast("Auto-capture complete!", "success", 2000);
}

// 4. File Upload Handler
function handleFileUpload(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    files.forEach(file => {
        if (capturedSamples.length >= 5) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            addSample(event.target.result);
        };
        reader.readAsDataURL(file);
    });

    fileUpload.value = "";
}

// 5. Add Sample to State & DOM
function addSample(b64) {
    capturedSamples.push(b64);
    renderSamples();
}

function removeSample(index) {
    capturedSamples.splice(index, 1);
    renderSamples();
}

function renderSamples() {
    counterBadge.textContent = `${capturedSamples.length} / 5 Samples`;

    if (capturedSamples.length === 0) {
        samplesContainer.innerHTML = `<span style="color: var(--text-subtle); font-size: 0.8rem; align-self: center; margin: auto;">No face samples captured yet.</span>`;
        return;
    }

    samplesContainer.innerHTML = capturedSamples.map((b64, idx) => `
        <div class="sample-thumb">
            <img src="${b64}" alt="Face sample #${idx+1}" />
            <button type="button" class="btn-remove-sample" onclick="removeSample(${idx})" title="Remove Sample">×</button>
        </div>
    `).join('');
}

// 6. Form Submission
async function submitEnrollment() {
    const studentId = document.getElementById("student_id").value.trim();
    const name = document.getElementById("name").value.trim();
    const department = document.getElementById("department").value.trim();
    const email = document.getElementById("email").value.trim();
    const phone = document.getElementById("phone").value.trim();
    const yearSemester = document.getElementById("year_semester").value.trim();
    const gender = document.getElementById("gender").value;

    if (!studentId || !name || !department) {
        showToast("Please fill in all required fields (Student ID, Name, Department).", "warning", 3500);
        return;
    }

    if (capturedSamples.length === 0) {
        showToast("Please capture or upload at least one face photo for AI enrollment.", "warning", 3500);
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = `
        <span class="status-indicator-dot" style="background: #fff; width: 6px; height: 6px;"></span>
        <span>Processing AI Enrollment...</span>
    `;

    try {
        const payload = {
            student_id: studentId,
            name: name,
            department: department,
            email: email,
            phone: phone,
            year_semester: yearSemester,
            gender: gender,
            images: capturedSamples
        };

        const res = await fetch("/api/students/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok && data.success) {
            playSound('success');
            showToast(`🎉 ${data.message}`, "success", 4000);

            // Clean up state
            capturedSamples = [];
            renderSamples();
            enrollForm.reset();

            // Offer navigation
            setTimeout(() => {
                const proceed = confirm("Student registered successfully! Would you like to go to the Live Scanner now to test face recognition?");
                if (proceed) {
                    window.location.href = "/scanner";
                }
            }, 600);
        } else {
            playSound('warning');
            showToast(`Registration failed: ${data.detail || data.message || "Unknown error"}`, "danger", 5000);
        }
    } catch (e) {
        console.error("Enrollment request error:", e);
        showToast("Network or server error during registration.", "danger", 4000);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>Register & Enroll Face</span>
        `;
    }
}

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
    btnStartCam.addEventListener("click", startEnrollCamera);
    btnSnap.addEventListener("click", captureSnapshot);
    btnAuto.addEventListener("click", startAutoCapture);
    fileUpload.addEventListener("change", handleFileUpload);
    submitBtn.addEventListener("click", submitEnrollment);

    document.getElementById("btn-reset-form").addEventListener("click", () => {
        capturedSamples = [];
        renderSamples();
    });
});
