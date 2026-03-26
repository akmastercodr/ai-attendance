// Configuration
const FRAME_INTERVAL = 300; // ms between frames
let cameraActive = true;
let stream = null;
let captureLoopId = null;

// UI Elements
const videoStream = document.getElementById('video-stream');
const detectionCanvas = document.getElementById('detection-canvas');
const ctx = detectionCanvas.getContext('2d');
const cameraBtn = document.getElementById('camera-toggle');
const streamOverlay = document.getElementById('stream-overlay');

// Navigation logic (Keep existing)
const navDashboard = document.getElementById('nav-dashboard');
const navUsers = document.getElementById('nav-users');
const navStudents = document.getElementById('nav-students');
const dashboardView = document.getElementById('dashboard-view');
const usersView = document.getElementById('users-view');

function switchView(viewId, activeNav) {
    dashboardView.style.display = viewId === 'dashboard' ? 'block' : 'none';
    usersView.style.display = viewId === 'users' ? 'block' : 'none';
    [navDashboard, navUsers, navStudents].forEach(nav => nav.classList.remove('active'));
    activeNav.classList.add('active');
}

navDashboard.addEventListener('click', (e) => { e.preventDefault(); switchView('dashboard', navDashboard); });
navUsers.addEventListener('click', (e) => { e.preventDefault(); switchView('users', navUsers); fetchRegisteredUsers(); addStudentBtn.style.display = 'none'; });
navStudents.addEventListener('click', (e) => { e.preventDefault(); switchView('users', navStudents); fetchRegisteredUsers('Student'); addStudentBtn.style.display = 'block'; });

// Camera Initialization
async function initCamera(videoElement) {
    try {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 }
        });
        videoElement.srcObject = stream;
        return true;
    } catch (err) {
        console.error("Error accessing camera:", err);
        alert("Could not access camera. Ensure you are using HTTPS and have given permission.");
        return false;
    }
}

// Frame Processing Loop
async function captureLoop() {
    if (!cameraActive) return;

    // Synchronize canvas size with video
    if (detectionCanvas.width !== videoStream.videoWidth) {
        detectionCanvas.width = videoStream.videoWidth;
        detectionCanvas.height = videoStream.videoHeight;
    }

    // Capture frame to dataURL
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = videoStream.videoWidth;
    tempCanvas.height = videoStream.videoHeight;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.drawImage(videoStream, 0, 0);
    const imageData = tempCanvas.toDataURL('image/jpeg', 0.7);

    try {
        const actionSelect = document.getElementById('attendance-mode');
        const currentAction = actionSelect ? actionSelect.value : 'ENTRY';
        
        const response = await fetch('/api/process_frame', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData, action: currentAction })
        });
        const data = await response.json();

        if (data.status === 'success') {
            drawDetections(data.results);
        }
    } catch (err) {
        console.error("Frame processing error:", err);
    }

    captureLoopId = setTimeout(captureLoop, FRAME_INTERVAL);
}

function drawDetections(results) {
    ctx.clearRect(0, 0, detectionCanvas.width, detectionCanvas.height);

    results.forEach(res => {
        const [x, y, w, h] = res.box;
        const color = res.identity === 'Unknown' ? '#ff3e3e' : '#3fb950';

        // Draw Box
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, w, h);

        // Draw Label
        ctx.fillStyle = color;
        ctx.font = 'bold 18px Inter, sans-serif';
        ctx.fillText(res.identity, x, y > 20 ? y - 10 : y + 20);
    });
}

// Toggle Camera
cameraBtn.onclick = () => {
    cameraActive = !cameraActive;
    if (cameraActive) {
        initCamera(videoStream).then(success => {
            if (success) {
                cameraBtn.innerHTML = '<i class="fas fa-video"></i> <span>Stop Camera</span>';
                cameraBtn.className = 'btn btn-primary';
                videoStream.style.opacity = '1';
                streamOverlay.innerText = 'LIVE STREAM';
                captureLoop();
            }
        });
    } else {
        if (stream) stream.getTracks().forEach(track => track.stop());
        clearTimeout(captureLoopId);
        ctx.clearRect(0, 0, detectionCanvas.width, detectionCanvas.height);
        cameraBtn.innerHTML = '<i class="fas fa-video-slash"></i> <span>Start Camera</span>';
        cameraBtn.className = 'btn btn-danger';
        videoStream.style.opacity = '0.3';
        streamOverlay.innerText = 'CAMERA OFF';
    }
};

// Registration Logic
const addStudentBtn = document.getElementById('add-student-btn');
const regModal = document.getElementById('reg-modal');
const regVideo = document.getElementById('reg-video');
const captureResult = document.getElementById('capture-result');
const snapPhotoBtn = document.getElementById('snap-photo');
const regForm = document.getElementById('reg-student-form');
const submitRegBtn = document.getElementById('submit-reg');
let capturedImageStore = null;

addStudentBtn.onclick = () => {
    regModal.style.display = 'flex';
    initCamera(regVideo);
    capturedImageStore = null;
    submitRegBtn.disabled = true;
    regForm.reset();
    captureResult.style.display = 'none';
    regVideo.style.display = 'block';
};

document.getElementById('close-reg-modal').onclick = () => {
    regModal.style.display = 'none';
    if (!cameraActive && stream) stream.getTracks().forEach(track => track.stop());
};

snapPhotoBtn.onclick = () => {
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = regVideo.videoWidth;
    tempCanvas.height = regVideo.videoHeight;
    tempCanvas.getContext('2d').drawImage(regVideo, 0, 0);
    capturedImageStore = tempCanvas.toDataURL('image/jpeg');

    captureResult.src = capturedImageStore;
    captureResult.style.display = 'block';
    regVideo.style.display = 'none';
    submitRegBtn.disabled = false;
};

regForm.onsubmit = async (e) => {
    e.preventDefault();
    const name = document.getElementById('reg-name').value;
    const dept = document.getElementById('reg-dept').value;

    submitRegBtn.disabled = true;
    submitRegBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';

    try {
        const response = await fetch('/api/register_student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, department: dept, image: capturedImageStore })
        });
        const data = await response.json();
        if (data.status === 'success') {
            alert(data.message);
            regModal.style.display = 'none';
            fetchRegisteredUsers('Student');
        } else {
            alert("Error: " + data.error);
        }
    } catch (err) {
        alert("Registration failed");
    } finally {
        submitRegBtn.disabled = false;
        submitRegBtn.innerHTML = '<i class="fas fa-user-plus"></i> Register';
    }
};

// Registered Users Logic
function fetchRegisteredUsers(roleFilter = null) {
    const title = document.querySelector('#users-view .section-title');
    title.innerText = roleFilter === 'Student' ? 'Registered Students' : 'Registered Personalities';

    fetch('/api/users')
        .then(response => response.json())
        .then(users => {
            const grid = document.getElementById('users-grid');
            grid.innerHTML = '';
            const filtered = roleFilter ? users.filter(u => u.metadata.role === roleFilter) : users;

            if (filtered.length === 0) {
                grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 4rem; color: var(--text-secondary);"><i class="fas fa-search fa-3x" style="margin-bottom: 1rem; opacity: 0.2;"></i><br>No registered users found.</div>';
                return;
            }

            filtered.forEach(user => {
                const initials = user.id.substring(0, 2).toUpperCase();
                const dept = user.metadata.department || 'General';
                const role = user.metadata.role || 'Visitor';

                const cardHTML = `
                    <div class="user-card glass">
                        <div class="user-avatar-large">${initials}</div>
                        <div class="user-info">
                            <div class="user-name">${user.id}</div>
                            <div class="user-meta-badge">${dept}</div>
                            <div class="user-meta-badge">${role}</div>
                        </div>
                        <div class="user-actions">
                            <button class="btn btn-primary btn-sm" onclick="editUser('${user.id}', '${dept}', '${role}')">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button class="btn btn-danger btn-sm" onclick="deleteUser('${user.id}')">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                `;
                grid.insertAdjacentHTML('beforeend', cardHTML);
            });
        });
}

async function deleteUser(userId) {
    if (!confirm(`Are you sure you want to delete ${userId}? This cannot be undone.`)) return;

    try {
        const response = await fetch(`/api/delete_user?id=${encodeURIComponent(userId)}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.status === 'success') {
            fetchRegisteredUsers(); // Refresh the list
        } else {
            alert("Error: " + data.error);
        }
    } catch (err) {
        alert("Delete failed. See console for details.");
        console.error(err);
    }
}

function editUser(id, dept, role) {
    document.getElementById('edit-user-id').value = id;
    document.getElementById('edit-user-name-display').value = id;
    document.getElementById('edit-user-dept').value = dept === 'General' ? '' : dept;
    document.getElementById('edit-user-role').value = role === 'Visitor' ? '' : role;
    document.getElementById('edit-modal').style.display = 'flex';
}

// Analytics Logic (Shared with old code)
function updateStats() {
    fetch('/api/stats').then(r => r.json()).then(data => {
        document.getElementById('stat-total').innerText = data.today_total || 0;
        document.getElementById('stat-unique').innerText = data.today_unique || 0;
    });
}

// Email Report Logic
const sendReportBtn = document.getElementById('send-report-btn');
const emailModal = document.getElementById('email-modal');
const emailForm = document.getElementById('email-report-form');
const closeEmailModal = document.getElementById('close-email-modal');
const cancelEmailBtn = document.getElementById('cancel-email');

sendReportBtn.onclick = () => {
    emailModal.style.display = 'flex';
};

closeEmailModal.onclick = cancelEmailBtn.onclick = () => {
    emailModal.style.display = 'none';
};

emailForm.onsubmit = async (e) => {
    e.preventDefault();
    const recipient = document.getElementById('report-recipient').value;
    const timeframe = document.getElementById('report-timeframe') ? document.getElementById('report-timeframe').value : 'today';
    const submitBtn = document.getElementById('confirm-send-email');

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    
    const requestBody = { recipient };
    if (timeframe === "all") {
        requestBody.date = "all";
    }

    try {
        const response = await fetch('/api/send_report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        const data = await response.json();

        if (data.status === 'success') {
            alert("Report sent successfully to " + recipient);
            emailModal.style.display = 'none';
            emailForm.reset();
        } else if (data.status === 'empty') {
            alert("No attendance records found for the selected timeframe. Email not sent.");
        } else {
            const errorMsg = data.message || data.error || JSON.stringify(data);
            alert("Error: " + errorMsg);
        }
    } catch (err) {
        alert("Failed to send report. Check console for details.");
        console.error(err);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Now';
    }
};

function updateActivityLog() {
    fetch('/api/attendance').then(r => r.json()).then(data => {
        const log = document.getElementById('activity-log');
        log.innerHTML = '';
        data.forEach(item => {
            const time = new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            // Generate visual badge based on ENTRY or EXIT action
            const isExit = item.action === 'EXIT';
            const actionBadge = isExit 
                ? '<span style="background-color: rgba(255, 62, 62, 0.2); color: #ff3e3e; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: 0.5rem; border: 1px solid rgba(255,62,62,0.3)">LEAVE</span>'
                : '<span style="background-color: rgba(63, 185, 80, 0.2); color: #3fb950; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: 0.5rem; border: 1px solid rgba(63,185,80,0.3)">ENTRY</span>';
                
            const iconColor = isExit ? '#ff3e3e' : '#3fb950';    
                
            log.insertAdjacentHTML('beforeend', `
                <div class="activity-item">
                    <div class="activity-avatar">${item.person_id.substring(0, 2).toUpperCase()}</div>
                    <div class="activity-info">
                        <span class="activity-name">${item.person_id} ${actionBadge}</span>
                        <span class="activity-time">${time} • ${(item.confidence * 100).toFixed(1)}%</span>
                    </div>
                    <i class="fas fa-check-circle" style="color: ${iconColor}"></i>
                </div>
            `);
        });
    });
}

function updateTime() {
    const timeElement = document.getElementById('current-time');
    const now = new Date();
    timeElement.innerText = now.toLocaleString('en-US', {
        weekday: 'short', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

// Initializing
initCamera(videoStream).then(success => {
    if (success) captureLoop();
});
setInterval(updateTime, 1000);
setInterval(updateStats, 5000);
setInterval(updateActivityLog, 2000);
updateTime(); updateStats(); updateActivityLog();
