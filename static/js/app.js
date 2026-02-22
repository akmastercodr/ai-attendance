// Navigation logic
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

navDashboard.addEventListener('click', (e) => {
    e.preventDefault();
    switchView('dashboard', navDashboard);
});

// Registration Modal logic
const addStudentBtn = document.getElementById('add-student-btn');
const regModal = document.getElementById('reg-modal');
const closeRegModal = document.getElementById('close-reg-modal');
const snapPhotoBtn = document.getElementById('snap-photo');
const regForm = document.getElementById('reg-student-form');
const captureCanvas = document.getElementById('capture-canvas');
const submitRegBtn = document.getElementById('submit-reg');
let capturedImage = null;

navStudents.addEventListener('click', (e) => {
    e.preventDefault();
    switchView('users', navStudents);
    fetchRegisteredUsers('Student');
    addStudentBtn.style.display = 'block'; // Show button in students view
});

navUsers.addEventListener('click', (e) => {
    e.preventDefault();
    switchView('users', navUsers);
    fetchRegisteredUsers();
    addStudentBtn.style.display = 'none'; // Hide in general users view
});

addStudentBtn.onclick = () => {
    regModal.style.display = 'flex';
    capturedImage = null;
    submitRegBtn.disabled = true;
    regForm.reset();

    // Reset preview
    document.getElementById('capture-result').style.display = 'none';
    document.getElementById('reg-stream').style.display = 'block';
    document.getElementById('capture-hint').innerText = 'Position the face and click "Capture Photo"';
};

closeRegModal.onclick = () => {
    regModal.style.display = 'none';
};

snapPhotoBtn.onclick = () => {
    snapPhotoBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Capturing...';
    snapPhotoBtn.disabled = true;

    fetch('/api/snapshot')
        .then(response => response.json())
        .then(data => {
            snapPhotoBtn.innerHTML = '<i class="fas fa-camera"></i> Capture Photo';
            snapPhotoBtn.disabled = false;

            if (data.image) {
                capturedImage = data.image;
                const resultImg = document.getElementById('capture-result');
                const streamImg = document.getElementById('reg-stream');
                const hint = document.getElementById('capture-hint');

                resultImg.src = capturedImage;
                resultImg.style.display = 'block';
                streamImg.style.display = 'none';
                hint.innerText = 'Photo captured! Click Register or snap again.';
                submitRegBtn.disabled = false;
            } else {
                alert('Capture failed: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(err => {
            snapPhotoBtn.innerHTML = '<i class="fas fa-camera"></i> Capture Photo';
            snapPhotoBtn.disabled = false;
            alert('Error connecting to camera API');
            console.error(err);
        });
};

regForm.onsubmit = (e) => {
    e.preventDefault();
    const name = document.getElementById('reg-name').value;
    const dept = document.getElementById('reg-dept').value;

    if (!capturedImage) {
        alert('Please capture a photo first!');
        return;
    }

    submitRegBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';
    submitRegBtn.disabled = true;

    fetch('/api/register_student', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: name,
            department: dept,
            image: capturedImage
        })
    })
        .then(response => response.json())
        .then(data => {
            submitRegBtn.innerHTML = '<i class="fas fa-user-plus"></i> Register';
            if (data.status === 'success') {
                alert(data.message);
                regModal.style.display = 'none';
                fetchRegisteredUsers('Student');
            } else {
                alert('Error: ' + data.error);
                submitRegBtn.disabled = false;
            }
        })
        .catch(error => {
            alert('Registration failed. Check console.');
            console.error(error);
            submitRegBtn.disabled = false;
        });
};

// Camera Toggle logic
const cameraBtn = document.getElementById('camera-toggle');
const mainStream = document.getElementById('main-stream');
const streamOverlay = document.getElementById('stream-overlay');

cameraBtn.addEventListener('click', () => {
    fetch('/api/toggle_camera', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.camera_on) {
                cameraBtn.innerHTML = '<i class="fas fa-video"></i> <span>Stop Camera</span>';
                cameraBtn.classList.remove('btn-danger');
                cameraBtn.classList.add('btn-primary');
                mainStream.style.opacity = '1';
                streamOverlay.innerText = 'LIVE STREAM';
                streamOverlay.classList.remove('alert');
            } else {
                cameraBtn.innerHTML = '<i class="fas fa-video-slash"></i> <span>Start Camera</span>';
                cameraBtn.classList.remove('btn-primary');
                cameraBtn.classList.add('btn-danger');
                mainStream.style.opacity = '0.3';
                streamOverlay.innerText = 'CAMERA OFF';
                streamOverlay.classList.add('alert');
            }
        });
});

// Modal logic
const editModal = document.getElementById('edit-modal');
const closeModal = document.getElementById('close-modal');
const cancelEdit = document.getElementById('cancel-edit');
const editForm = document.getElementById('edit-user-form');

function openEditModal(userId, name, dept, role) {
    document.getElementById('edit-user-id').value = userId;
    document.getElementById('edit-user-name-display').value = name;
    document.getElementById('edit-user-dept').value = dept || '';
    document.getElementById('edit-user-role').value = role || '';
    editModal.style.display = 'flex';
}

function closeEditModal() {
    editModal.style.display = 'none';
}

closeModal.onclick = closeEditModal;
cancelEdit.onclick = closeEditModal;
window.onclick = (event) => {
    if (event.target == editModal) closeEditModal();
};

editForm.onsubmit = (e) => {
    e.preventDefault();
    const id = document.getElementById('edit-user-id').value;
    const dept = document.getElementById('edit-user-dept').value;
    const role = document.getElementById('edit-user-role').value;

    fetch('/api/update_user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            id: id,
            metadata: { department: dept, role: role }
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('User updated successfully!');
                closeEditModal();
                fetchRegisteredUsers();
            } else {
                alert('Error: ' + data.error);
            }
        });
};

function fetchRegisteredUsers(roleFilter = null) {
    const title = document.querySelector('#users-view .section-title');
    title.innerText = roleFilter === 'Student' ? 'Registered Students' : 'Registered Personalities';

    fetch('/api/users')
        .then(response => response.json())
        .then(users => {
            const grid = document.getElementById('users-grid');
            grid.innerHTML = '';

            const filteredUsers = roleFilter
                ? users.filter(u => u.metadata.role === roleFilter)
                : users;

            if (filteredUsers.length === 0) {
                grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-secondary); padding: 2rem;">No ${roleFilter || 'users'} found.</div>`;
                return;
            }

            filteredUsers.forEach(user => {
                const initials = user.id.substring(0, 2).toUpperCase();
                const dept = user.metadata.department || 'N/A';
                const role = user.metadata.role || 'N/A';

                const card = `
                    <div class="user-card">
                        <div class="user-avatar-large">${initials}</div>
                        <div class="user-name">${user.id}</div>
                        <div class="user-meta">DEP: ${dept}</div>
                        <div class="user-meta">ROLE: ${role}</div>
                        <button class="btn btn-primary" style="width: 100%; font-size: 0.8rem; margin-top: 0.5rem;" 
                                onclick="openEditModal('${user.id}', '${user.id}', '${dept}', '${role}')">
                            <i class="fas fa-edit"></i> Edit Details
                        </button>
                    </div>
                `;
                grid.insertAdjacentHTML('beforeend', card);
            });
        });
}

function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('stat-total').innerText = data.today_total || 0;
            document.getElementById('stat-unique').innerText = data.today_unique || 0;
        })
        .catch(error => console.error('Error fetching stats:', error));
}

function updateActivityLog() {
    fetch('/api/attendance')
        .then(response => response.json())
        .then(data => {
            const logContainer = document.getElementById('activity-log');
            logContainer.innerHTML = '';

            data.forEach(item => {
                const time = new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const initials = item.person_id ? item.person_id.substring(0, 2).toUpperCase() : '??';

                const html = `
                    <div class="activity-item">
                        <div class="activity-avatar">${initials}</div>
                        <div class="activity-info">
                            <span class="activity-name">${item.person_id}</span>
                            <span class="activity-time">${time} • Confidence: ${(item.confidence * 100).toFixed(1)}%</span>
                        </div>
                        <i class="fas fa-check-circle" style="color: #3fb950"></i>
                    </div>
                `;
                logContainer.insertAdjacentHTML('beforeend', html);
            });
        })
        .catch(error => console.error('Error fetching activity:', error));
}

function updateTime() {
    const timeElement = document.getElementById('current-time');
    const now = new Date();
    timeElement.innerText = now.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Update loops
setInterval(updateTime, 1000);
setInterval(updateStats, 5000);
setInterval(updateActivityLog, 2000);

// Initial call
updateTime();
updateStats();
updateActivityLog();
