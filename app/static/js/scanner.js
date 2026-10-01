// ==========================================================================
// AI Attendance System - Real-time Webcam Face Recognition Scanner
// ==========================================================================

let videoStream = null;
let isScanning = false;
let isProcessingFrame = false;
let soundEnabled = true;
let currentCameraMode = "browser";
let activeDeviceIndex = 0;
let availableVideoDevices = [];
let sessionScansCount = 0;

const videoEl = document.getElementById("scanner-video");
const overlayCanvas = document.getElementById("scanner-overlay");
const serverImg = document.getElementById("server-stream-img");
const placeholder = document.getElementById("camera-placeholder");

const btnStart = document.getElementById("btn-start-camera");
const btnStop = document.getElementById("btn-stop-camera");
const btnFlip = document.getElementById("btn-flip-camera");
const btnSound = document.getElementById("btn-toggle-sound");
const modeSelect = document.getElementById("camera-mode-select");

const scannerDot = document.getElementById("scanner-dot");
const scannerStatusText = document.getElementById("scanner-status-text");

// Offscreen canvas for grabbing frames
const captureCanvas = document.createElement("canvas");
const captureCtx = captureCanvas.getContext("2d");

// 1. Camera Initialization (Browser WebRTC)
async function startBrowserCamera() {
    try {
        scannerStatusText.textContent = "Connecting Camera...";
        
        // Enumerate video devices
        const devices = await navigator.mediaDevices.enumerateDevices();
        availableVideoDevices = devices.filter(d => d.kind === 'videoinput');

        const constraints = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                deviceId: availableVideoDevices[activeDeviceIndex] ? { exact: availableVideoDevices[activeDeviceIndex].deviceId } : undefined
            },
            audio: false
        };

        videoStream = await navigator.mediaDevices.getUserMedia(constraints);
        videoEl.srcObject = videoStream;
        await videoEl.play();

        // Match overlay canvas size to video display
        videoEl.onloadedmetadata = () => {
            overlayCanvas.width = videoEl.videoWidth || 640;
            overlayCanvas.height = videoEl.videoHeight || 480;
            captureCanvas.width = 640;
            captureCanvas.height = 480;
        };

        videoEl.style.display = "block";
        serverImg.style.display = "none";
        placeholder.style.display = "none";
        btnStart.style.display = "none";
        btnStop.style.display = "inline-flex";

        scannerDot.style.backgroundColor = "#10B981";
        scannerDot.style.boxShadow = "0 0 8px #10B981";
        scannerStatusText.textContent = "AI Scanning Active";

        isScanning = true;
        requestAnimationFrame(scannerLoop);
        showToast("Webcam active. Scanning for faces...", "success", 3000);
    } catch (err) {
        console.error("Camera access error:", err);
        scannerStatusText.textContent = "Camera Error";
        scannerDot.style.backgroundColor = "#EF4444";
        showToast("Could not access camera. Please allow camera permissions.", "danger", 5000);
    }
}

// 2. Stop Camera
function stopCamera() {
    isScanning = false;
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
    videoEl.srcObject = null;
    videoEl.style.display = "none";
    serverImg.style.display = "none";
    serverImg.src = "";
    placeholder.style.display = "flex";

    btnStart.style.display = "inline-flex";
    btnStop.style.display = "none";

    scannerDot.style.backgroundColor = "#EF4444";
    scannerDot.style.boxShadow = "0 0 8px #EF4444";
    scannerStatusText.textContent = "Camera Idle";

    // Clear overlay
    const ctx = overlayCanvas.getContext("2d");
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
}

// 3. Server Local Webcam Stream Mode
function startServerStream() {
    videoEl.style.display = "none";
    serverImg.style.display = "block";
    placeholder.style.display = "none";
    serverImg.src = "/api/system/camera/stream?" + new Date().getTime();

    btnStart.style.display = "none";
    btnStop.style.display = "inline-flex";

    scannerDot.style.backgroundColor = "#10B981";
    scannerDot.style.boxShadow = "0 0 8px #10B981";
    scannerStatusText.textContent = "OpenCV Server Feed Active";
    showToast("Connected to Server Webcam stream.", "info", 3000);
}

// 4. Real-time Recognition Loop (Browser Mode)
let lastFrameTime = 0;
const FRAME_INTERVAL = 140; // ~7 frames per second for smooth low-latency AI

async function scannerLoop(timestamp) {
    if (!isScanning) return;

    if (timestamp - lastFrameTime >= FRAME_INTERVAL && !isProcessingFrame) {
        lastFrameTime = timestamp;
        await processCurrentFrame();
    }

    requestAnimationFrame(scannerLoop);
}

async function processCurrentFrame() {
    if (!videoEl.videoWidth || !videoEl.videoHeight) return;

    isProcessingFrame = true;

    try {
        // Draw video frame to downscaled capture canvas
        captureCtx.drawImage(videoEl, 0, 0, captureCanvas.width, captureCanvas.height);
        const b64Image = captureCanvas.toDataURL("image/jpeg", 0.75);

        const res = await fetch("/api/attendance/recognize-frame", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: b64Image })
        });

        const data = await res.json();
        if (data.success && data.data) {
            renderDetections(data.data.faces || []);
            handleAttendanceEvents(data.data.events || []);
        }
    } catch (e) {
        console.warn("Frame recognition error:", e);
    } finally {
        isProcessingFrame = false;
    }
}

// 5. Render HUD Bounding Boxes on Overlay Canvas
function renderDetections(faces) {
    const ctx = overlayCanvas.getContext("2d");
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    if (!faces || faces.length === 0) return;

    // Scale factors between capture resolution (640x480) and display overlay resolution
    const scaleX = overlayCanvas.width / captureCanvas.width;
    const scaleY = overlayCanvas.height / captureCanvas.height;

    faces.forEach(f => {
        const [x, y, w, h] = f.box;
        const dx = x * scaleX;
        const dy = y * scaleY;
        const dw = w * scaleX;
        const dh = h * scaleY;

        let strokeColor = "#EF4444"; // Red for unknown
        let bgColor = "rgba(239, 68, 68, 0.85)";
        let title = "Unknown Face";
        let sub = "Not Registered";

        if (f.status_type === 'newly_marked') {
            strokeColor = "#10B981"; // Green
            bgColor = "rgba(16, 185, 129, 0.9)";
            title = f.name;
            sub = `Attendance Marked! (${f.confidence_pct}%)`;
        } else if (f.status_type === 'already_marked') {
            strokeColor = "#38BDF8"; // Cyan
            bgColor = "rgba(56, 189, 248, 0.9)";
            title = f.name;
            sub = `Already Marked Today`;
        }

        // Draw HUD Bracket Box
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 3;
        ctx.beginPath();
        const cornerLen = Math.min(20, dw * 0.25);

        // Top-left
        ctx.moveTo(dx, dy + cornerLen);
        ctx.lineTo(dx, dy);
        ctx.lineTo(dx + cornerLen, dy);

        // Top-right
        ctx.moveTo(dx + dw - cornerLen, dy);
        ctx.lineTo(dx + dw, dy);
        ctx.lineTo(dx + dw, dy + cornerLen);

        // Bottom-right
        ctx.moveTo(dx + dw, dy + dh - cornerLen);
        ctx.lineTo(dx + dw, dy + dh);
        ctx.lineTo(dx + dw - cornerLen, dy + dh);

        // Bottom-left
        ctx.moveTo(dx + cornerLen, dy + dh);
        ctx.lineTo(dx, dy + dh);
        ctx.lineTo(dx, dy + dh - cornerLen);
        ctx.stroke();

        // Semi-transparent target fill
        ctx.fillStyle = strokeColor + "15";
        ctx.fillRect(dx, dy, dw, dh);

        // Name Banner
        ctx.save();
        // Un-mirror text because overlay canvas is CSS mirrored scaleX(-1)
        ctx.translate(dx + dw / 2, dy - 18);
        ctx.scale(-1, 1);

        const bannerWidth = Math.max(160, dw);
        ctx.fillStyle = bgColor;
        ctx.beginPath();
        ctx.roundRect(-bannerWidth / 2, -18, bannerWidth, 36, 6);
        ctx.fill();

        ctx.fillStyle = "#FFFFFF";
        ctx.font = "bold 13px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(title, 0, -2);

        ctx.font = "10px Inter, sans-serif";
        ctx.fillStyle = "#F1F5F9";
        ctx.fillText(sub, 0, 11);
        ctx.restore();
    });
}

// 6. Handle Attendance Events (Toasts, Chimes & Cards)
function handleAttendanceEvents(events) {
    if (!events || events.length === 0) return;

    events.forEach(ev => {
        if (ev.type === 'marked') {
            if (soundEnabled) playSound('success');
            showToast(`✅ ${ev.name} marked ${ev.status}!`, 'success', 3500);
            updateRecognitionCard(ev, 'marked');
            prependSessionLog(ev, 'marked');
        } else if (ev.type === 'duplicate') {
            if (soundEnabled) playSound('duplicate');
            showToast(`ℹ️ ${ev.name} already checked in at ${ev.time}`, 'warning', 3000);
            updateRecognitionCard(ev, 'duplicate');
            prependSessionLog(ev, 'duplicate');
        }
    });
}

// 7. Update Live Result Card
function updateRecognitionCard(ev, type) {
    const card = document.getElementById("student-live-card");
    const nameEl = document.getElementById("recog-name");
    const idEl = document.getElementById("recog-id");
    const deptEl = document.getElementById("recog-dept");
    const timeEl = document.getElementById("recog-time");
    const confEl = document.getElementById("recog-conf");
    const badgeEl = document.getElementById("recog-status-badge");
    const avatar = document.getElementById("recog-avatar");

    nameEl.textContent = ev.name || "Student";
    idEl.textContent = "ID: " + (ev.student_id || "---");
    deptEl.textContent = "Dept: " + (ev.department || "General");
    timeEl.textContent = ev.time || "--:--:--";
    confEl.textContent = ev.confidence ? `${ev.confidence}%` : "100%";

    avatar.src = `/static/faces/${ev.student_id}/sample_1.jpg`;
    avatar.onerror = () => {
        avatar.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='60' height='60' viewBox='0 0 24 24' fill='none' stroke='%2364748B' stroke-width='1.5'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>";
    };

    if (type === 'marked') {
        card.style.borderLeftColor = "#10B981";
        badgeEl.className = "badge badge-present";
        badgeEl.textContent = `Present (${ev.status || 'On-time'})`;
    } else {
        card.style.borderLeftColor = "#38BDF8";
        badgeEl.className = "badge badge-info";
        badgeEl.textContent = "Already Checked In";
    }
}

// 8. Session Activity Log List
function prependSessionLog(ev, type) {
    sessionScansCount++;
    const countBadge = document.getElementById("session-count-badge");
    if (countBadge) countBadge.textContent = `${sessionScansCount} Scans`;

    const list = document.getElementById("session-logs-list");
    if (!list) return;

    if (sessionScansCount === 1) {
        list.innerHTML = "";
    }

    const item = document.createElement("div");
    item.style.display = "flex";
    item.style.alignItems = "center";
    item.style.justifyContent = "space-between";
    item.style.padding = "0.6rem 0.85rem";
    item.style.background = "var(--bg-input)";
    item.style.borderRadius = "var(--radius-sm)";
    item.style.border = "1px solid var(--border-color)";

    const isMarked = type === 'marked';
    const badgeHtml = isMarked
        ? `<span class="badge badge-present">${ev.status || 'Present'}</span>`
        : `<span class="badge badge-info">Duplicate</span>`;

    item.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.65rem;">
            <div style="font-weight: 600; font-size: 0.85rem; color: var(--text-main);">${ev.name}</div>
            <span style="font-size: 0.75rem; color: var(--text-subtle); font-family: monospace;">${ev.student_id}</span>
        </div>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 0.78rem; font-family: monospace; color: var(--text-muted);">${ev.time}</span>
            ${badgeHtml}
        </div>
    `;

    list.prepend(item);
}

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
    btnStart.addEventListener("click", () => {
        if (currentCameraMode === "browser") {
            startBrowserCamera();
        } else {
            startServerStream();
        }
    });

    btnStop.addEventListener("click", stopCamera);

    btnFlip.addEventListener("click", () => {
        if (availableVideoDevices.length > 1) {
            activeDeviceIndex = (activeDeviceIndex + 1) % availableVideoDevices.length;
            if (isScanning) {
                stopCamera();
                startBrowserCamera();
            }
        } else {
            showToast("No alternative camera device found.", "info", 2000);
        }
    });

    btnSound.addEventListener("click", () => {
        soundEnabled = !soundEnabled;
        const soundText = document.getElementById("sound-btn-text");
        if (soundEnabled) {
            soundText.textContent = "Audio On";
            btnSound.style.color = "var(--text-main)";
            showToast("Audio chimes enabled", "info", 1500);
        } else {
            soundText.textContent = "Muted";
            btnSound.style.color = "var(--text-subtle)";
            showToast("Audio chimes muted", "info", 1500);
        }
    });

    modeSelect.addEventListener("change", (e) => {
        currentCameraMode = e.target.value;
        if (isScanning) {
            stopCamera();
            if (currentCameraMode === "browser") {
                startBrowserCamera();
            } else {
                startServerStream();
            }
        }
    });
});
