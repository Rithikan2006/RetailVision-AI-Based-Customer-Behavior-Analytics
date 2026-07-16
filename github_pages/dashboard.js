// Retrieve User Role from LocalStorage
const userRole = localStorage.getItem('role') || 'guest';
document.getElementById('user-role-badge').textContent = `Role: ${userRole.charAt(0).toUpperCase() + userRole.slice(1)}`;

if (userRole === 'admin') {
    document.getElementById('admin-reset-btn').classList.remove('d-none');
}

// Zone Coordinate Maps (X1, Y1, X2, Y2)
const zones = {
    'Entrance': [0, 500, 250, 720],
    'Vegetables': [100, 100, 450, 400],
    'Snacks': [550, 100, 900, 400],
    'Beverages': [950, 100, 1280, 500],
    'Billing': [950, 500, 1280, 720]
};

// State Variables
let simulatedCustomers = [];
let nextCustomerId = 1;
let activeAlerts = [];
let heatmapPoints = [];
let totalVisitorsCount = 120; // Seed with historical numbers
let totalDwellTime = 120 * 45; // average 45s stay
let peakHour = "18:00";
let peakHourCount = 38;

// Analytics Seed Data
let zoneVisits = {
    'Vegetables': { visits: 85, avgDwell: 34 },
    'Snacks': { visits: 72, avgDwell: 22 },
    'Beverages': { visits: 60, avgDwell: 18 },
    'Billing': { visits: 112, avgDwell: 55 }
};

let hourlyVisits = {
    "08:00": 3, "09:00": 8, "10:00": 12, "11:00": 15, "12:00": 28,
    "13:00": 32, "14:00": 20, "15:00": 18, "16:00": 22, "17:00": 35,
    "18:00": 38, "19:00": 34, "20:00": 25, "21:00": 12, "22:00": 4
};

// Canvas Setup
const videoCanvas = document.getElementById('video-canvas');
const videoCtx = videoCanvas.getContext('2d');

const heatmapCanvas = document.getElementById('heatmap-canvas');
const heatmapCtx = heatmapCanvas.getContext('2d');

// Chart Instances
let hourlyChartInstance = null;
let zoneChartInstance = null;

// Initialize System
window.addEventListener('DOMContentLoaded', () => {
    initCharts();
    initHeatmapPoints();
    
    // Start canvas loops
    requestAnimationFrame(animationLoop);
    
    // Spawn customer timer
    setInterval(spawnCustomer, 3000);
    
    // Update dashboard statistics periodic
    setInterval(updateStatsUI, 2000);
});

// Seed Initial Heatmap Points for visualization
function initHeatmapPoints() {
    // Generate cluster points in zones to represent history
    for (let zoneName in zones) {
        if (zoneName === 'Entrance') continue;
        const box = zones[zoneName];
        const count = zoneName === 'Vegetables' || zoneName === 'Billing' ? 80 : 40;
        for (let i = 0; i < count; i++) {
            heatmapPoints.push({
                x: box[0] + 50 + Math.random() * (box[2] - box[0] - 100),
                y: box[1] + 50 + Math.random() * (box[3] - box[1] - 100),
                weight: Math.random()
            });
        }
    }
}

// Chart.js Setup
function initCharts() {
    // 1. Hourly Chart
    const ctxHourly = document.getElementById('hourlyChart').getContext('2d');
    hourlyChartInstance = new Chart(ctxHourly, {
        type: 'line',
        data: {
            labels: Object.keys(hourlyVisits),
            datasets: [{
                label: 'Visitors',
                data: Object.values(hourlyVisits),
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.15)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#6366f1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#94a3b8', font: { size: 9 } } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' }, beginAtZero: true }
            }
        }
    });

    // 2. Zone Chart
    const ctxZone = document.getElementById('zoneChart').getContext('2d');
    zoneChartInstance = new Chart(ctxZone, {
        type: 'bar',
        data: {
            labels: ['Vegetables', 'Snacks', 'Beverages', 'Billing'],
            datasets: [{
                label: 'Visits',
                data: ['Vegetables', 'Snacks', 'Beverages', 'Billing'].map(z => zoneVisits[z].visits),
                backgroundColor: [
                    'rgba(16, 185, 129, 0.75)',
                    'rgba(59, 130, 246, 0.75)',
                    'rgba(6, 182, 212, 0.75)',
                    'rgba(249, 115, 22, 0.75)'
                ],
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' }, beginAtZero: true }
            }
        }
    });
}

// Spawns a customer inside the simulation
function spawnCustomer() {
    if (simulatedCustomers.length >= 15) return; // Cap simultaneous customers
    
    // Choose path: Entrance -> Shopping zones (random 1-3) -> Billing -> Exit
    const shoppingSpots = ['Vegetables', 'Snacks', 'Beverages'];
    // Shuffle spots
    shoppingSpots.sort(() => Math.random() - 0.5);
    const path = ['Entrance', ...shoppingSpots.slice(0, Math.floor(Math.random() * 3) + 1), 'Billing', 'Exit'];
    
    // Random position in Entrance
    const startBox = zones['Entrance'];
    const startX = startBox[0] + Math.random() * (startBox[2] - startBox[0]);
    const startY = startBox[1] + Math.random() * (startBox[3] - startBox[1]);

    simulatedCustomers.push({
        id: nextCustomerId++,
        x: startX,
        y: startY,
        path: path,
        pathIndex: 1, // Start moving towards first shopping spot
        targetX: null,
        targetY: null,
        state: 'moving', // moving, shopping
        dwellTimer: 0,
        speed: 1.5 + Math.random() * 2,
        currentZone: 'Entrance',
        shelfDwellTime: 0 // Tracks dwell time at a specific shelf
    });

    totalVisitorsCount++;
    addAlert(`Customer #${nextCustomerId - 1} entered the store.`);
    
    // Add visitor to current hour trend
    const currentHourStr = `${new Date().getHours().toString().padStart(2, '0')}:00`;
    if (hourlyVisits[currentHourStr] !== undefined) {
        hourlyVisits[currentHourStr]++;
    }
}

// Main Frame loop for canvases
function animationLoop() {
    updateCustomerPhysics();
    drawCCTVStream();
    drawHeatmap();
    requestAnimationFrame(animationLoop);
}

// Updates simulated customer coordinates
function updateCustomerPhysics() {
    for (let i = simulatedCustomers.length - 1; i >= 0; i--) {
        const cust = simulatedCustomers[i];
        const targetZone = cust.path[cust.pathIndex];
        
        if (cust.targetX === null || cust.targetY === null) {
            if (targetZone === 'Exit') {
                cust.targetX = -30;
                cust.targetY = 600;
            } else {
                const box = zones[targetZone];
                cust.targetX = box[0] + 30 + Math.random() * (box[2] - box[0] - 60);
                cust.targetY = box[1] + 30 + Math.random() * (box[3] - box[1] - 60);
            }
        }

        const dx = cust.targetX - cust.x;
        const dy = cust.targetY - cust.y;
        const dist = Math.hypot(dx, dy);

        if (cust.state === 'moving') {
            if (dist > 5) {
                cust.x += (dx / dist) * cust.speed;
                cust.y += (dy / dist) * cust.speed;
                // Add coordinates to heatmap points periodically (with probability)
                if (Math.random() < 0.04) {
                    heatmapPoints.push({ x: cust.x, y: cust.y, weight: 0.1 });
                    if (heatmapPoints.length > 3000) heatmapPoints.shift(); // Cap memory size
                }
            } else {
                // Reached target
                if (targetZone === 'Exit') {
                    // Log total stay duration
                    const staySeconds = 25 + Math.floor(Math.random() * 50);
                    totalDwellTime += staySeconds;
                    
                    addAlert(`Customer #${cust.id} exited the store.`);
                    simulatedCustomers.splice(i, 1);
                    continue;
                }
                
                // Start Shopping/Dwelling
                cust.state = 'shopping';
                cust.dwellTimer = 80 + Math.floor(Math.random() * 150); // dwell frames
                cust.currentZone = targetZone;
                
                // Add visit count
                if (zoneVisits[targetZone]) {
                    zoneVisits[targetZone].visits++;
                }
            }
        } else if (cust.state === 'shopping') {
            cust.dwellTimer--;
            cust.shelfDwellTime++;
            
            // Add coordinate points to heatmap during shopping
            if (Math.random() < 0.1) {
                heatmapPoints.push({ x: cust.x, y: cust.y, weight: 0.2 });
            }

            // Shelf Dwell Alert check (60 frames approx 2 seconds. 600 frames = 20 seconds)
            if (cust.shelfDwellTime === 600 && ['Vegetables', 'Snacks', 'Beverages'].includes(cust.currentZone)) {
                addAlert(`Customer #${cust.id} shows high interest in ${cust.currentZone} (Stayed > 20s).`, 'warning');
            }

            if (cust.dwellTimer <= 0) {
                // Move to next zone
                cust.pathIndex++;
                cust.state = 'moving';
                cust.targetX = null;
                cust.targetY = null;
                cust.shelfDwellTime = 0;
            }
        }
    }
}

// Draws the CCTV Blueprint interface
function drawCCTVStream() {
    videoCtx.fillStyle = '#0f172a'; // Slate darkest background
    videoCtx.fillRect(0, 0, videoCanvas.width, videoCanvas.height);

    // Draw Floor grid lines
    videoCtx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
    videoCtx.lineWidth = 1;
    for (let x = 0; x < videoCanvas.width; x += 40) {
        videoCtx.beginPath();
        videoCtx.moveTo(x, 0);
        videoCtx.lineTo(x, videoCanvas.height);
        videoCtx.stroke();
    }
    for (let y = 0; y < videoCanvas.height; y += 40) {
        videoCtx.beginPath();
        videoCtx.moveTo(0, y);
        videoCtx.lineTo(videoCanvas.width, y);
        videoCtx.stroke();
    }

    // Draw Zones
    for (let name in zones) {
        const box = zones[name];
        const isBilling = name === 'Billing';
        
        // Transparent fill
        videoCtx.fillStyle = isBilling ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.04)';
        videoCtx.fillRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);
        
        // Borders
        videoCtx.strokeStyle = isBilling ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)';
        videoCtx.lineWidth = 2;
        videoCtx.strokeRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);

        // Zone Name
        videoCtx.fillStyle = isBilling ? 'rgba(239, 68, 68, 0.7)' : 'rgba(16, 185, 129, 0.7)';
        videoCtx.font = 'bold 16px Outfit';
        videoCtx.fillText(name, box[0] + 15, box[1] + 30);
    }

    // Draw Physical Virtual Shelves (Shelf A & Shelf B)
    drawShelf(400, 100, 100, 500, "SHELF A");
    drawShelf(750, 100, 100, 500, "SHELF B");

    // Draw Customers Bounding boxes and labels
    simulatedCustomers.forEach(cust => {
        const cx = cust.x;
        const cy = cust.y;
        
        // Bounding box size: width 60, height 100
        const w = 60;
        const h = 100;
        const x = cx - w/2;
        const y = cy - h + 20;

        // Draw Bounding box border
        videoCtx.strokeStyle = '#f97316'; // Orange bounding boxes
        videoCtx.lineWidth = 2;
        videoCtx.strokeRect(x, y, w, h);

        // Center dot
        videoCtx.fillStyle = '#ef4444';
        videoCtx.beginPath();
        videoCtx.arc(cx, cy, 4, 0, Math.PI * 2);
        videoCtx.fill();

        // Label Tag
        videoCtx.fillStyle = 'rgba(249, 115, 22, 0.85)';
        videoCtx.fillRect(x, y - 22, w + 30, 22);
        
        videoCtx.fillStyle = '#ffffff';
        videoCtx.font = '600 11px Outfit';
        videoCtx.fillText(`ID: ${cust.id} | ${cust.currentZone}`, x + 5, y - 7);
    });

    // Draw Overall occupancy overlay info
    videoCtx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    videoCtx.fillRect(15, 15, 280, 100);
    videoCtx.strokeStyle = 'rgba(255,255,255,0.05)';
    videoCtx.strokeRect(15, 15, 280, 100);
    
    videoCtx.fillStyle = '#ffffff';
    videoCtx.font = '500 14px Outfit';
    videoCtx.fillText(`Active Tracks inside: ${simulatedCustomers.length}`, 30, 42);
    
    // Billing Queue Length
    const billingCount = simulatedCustomers.filter(c => c.currentZone === 'Billing').length;
    videoCtx.fillStyle = billingCount >= 10 ? '#ef4444' : '#ffffff';
    videoCtx.fillText(`Billing Queue Length: ${billingCount}`, 30, 67);
    
    videoCtx.fillStyle = '#94a3b8';
    videoCtx.font = '500 12px Outfit';
    videoCtx.fillText(`AI Model: YOLOv8n (Embedded Simulation)`, 30, 92);
}

function drawShelf(x, y, w, h, label) {
    videoCtx.fillStyle = '#1e293b';
    videoCtx.fillRect(x, y, w, h);
    videoCtx.strokeStyle = 'rgba(255,255,255,0.1)';
    videoCtx.strokeRect(x, y, w, h);
    
    videoCtx.save();
    videoCtx.translate(x + w/2, y + h/2);
    videoCtx.rotate(-Math.PI / 2);
    videoCtx.fillStyle = '#475569';
    videoCtx.font = 'bold 16px Outfit';
    videoCtx.textAlign = 'center';
    videoCtx.fillText(label, 0, 5);
    videoCtx.restore();
}

// Draws the traffic density Heatmap overlay on canvas
function drawHeatmap() {
    heatmapCtx.fillStyle = '#0f172a';
    heatmapCtx.fillRect(0, 0, heatmapCanvas.width, heatmapCanvas.height);

    // Draw background blueprint elements in grayscale
    for (let name in zones) {
        const box = zones[name];
        heatmapCtx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        heatmapCtx.strokeRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);
        heatmapCtx.fillStyle = 'rgba(255, 255, 255, 0.02)';
        heatmapCtx.fillText(name, box[0] + 15, box[1] + 30);
    }
    
    // Draw shelves outline
    heatmapCtx.fillStyle = '#111827';
    heatmapCtx.fillRect(400, 100, 100, 500);
    heatmapCtx.fillRect(750, 100, 100, 500);

    // Composite operation to blend overlapping radial gradients (creates colormap density)
    heatmapCtx.save();
    heatmapCtx.globalCompositeOperation = 'screen';

    heatmapPoints.forEach(pt => {
        const grad = heatmapCtx.createRadialGradient(pt.x, pt.y, 1, pt.x, pt.y, 25);
        // Colormap blending stops
        grad.addColorStop(0, 'rgba(239, 68, 68, 0.15)');  // Red high density
        grad.addColorStop(0.4, 'rgba(234, 179, 8, 0.06)'); // Yellow medium
        grad.addColorStop(0.8, 'rgba(59, 130, 246, 0.02)'); // Blue low
        grad.addColorStop(1, 'rgba(0, 0, 255, 0)');        // Transparent boundary
        
        heatmapCtx.fillStyle = grad;
        heatmapCtx.beginPath();
        heatmapCtx.arc(pt.x, pt.y, 25, 0, Math.PI * 2);
        heatmapCtx.fill();
    });
    heatmapCtx.restore();
}

// Add system alerts
function addAlert(message, type = 'normal') {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    activeAlerts.push({ time: timestamp, message, type });
    if (activeAlerts.length > 20) activeAlerts.shift();

    // Check Billing queue overflow alert
    const billingCount = simulatedCustomers.filter(c => c.currentZone === 'Billing').length;
    if (billingCount >= 10 && !activeAlerts.some(a => a.message.includes('Queue is congested') && a.type === 'danger')) {
        activeAlerts.push({
            time: timestamp,
            message: `ALERT: Billing Queue is congested! ${billingCount} customers in queue.`,
            type: 'danger'
        });
    }

    // Check occupancy overflow
    if (simulatedCustomers.length >= 12 && !activeAlerts.some(a => a.message.includes('Crowd capacity') && a.type === 'danger')) {
        activeAlerts.push({
            time: timestamp,
            message: `ALERT: Crowd capacity warning! ${simulatedCustomers.length} active tracks.`,
            type: 'danger'
        });
    }
}

// Updates Stats KPIs on the UI
function updateStatsUI() {
    // KPIs
    document.getElementById('kpi-total').textContent = totalVisitorsCount;
    document.getElementById('kpi-current').textContent = simulatedCustomers.length;
    document.getElementById('kpi-dwell').textContent = `${Math.round(totalDwellTime / Math.max(1, totalVisitorsCount))}s`;
    document.getElementById('kpi-peak').textContent = `${peakHour} (${peakHourCount} visits)`;

    // Alerts Feed Panel
    const alertsContainer = document.getElementById('alerts-container');
    const indicator = document.getElementById('alert-indicator');
    
    if (activeAlerts.length === 0) {
        alertsContainer.innerHTML = '<div class="text-center py-4 text-muted" style="font-size:0.85rem;">No active alerts. Monitoring...</div>';
        indicator.className = "badge bg-success";
        indicator.textContent = "Normal";
    } else {
        const hasDanger = activeAlerts.some(a => a.type === 'danger');
        if (hasDanger) {
            indicator.className = "badge bg-danger animate-pulse";
            indicator.textContent = "Alert Active";
        } else {
            indicator.className = "badge bg-primary";
            indicator.textContent = "Monitoring";
        }

        let html = '';
        [...activeAlerts].reverse().forEach(alert => {
            let alertClass = '';
            if (alert.type === 'danger') alertClass = 'alert-danger';
            else if (alert.type === 'warning') alertClass = 'alert-warning';
            
            html += `
                <div class="alert-item ${alertClass}">
                    <div class="alert-time">${alert.time}</div>
                    <div>${alert.message}</div>
                </div>
            `;
        });
        alertsContainer.innerHTML = html;
    }

    // Zone Breakdown Table
    const tableBody = document.getElementById('zone-table-body');
    let tableHtml = '';
    const zonesList = ['Vegetables', 'Snacks', 'Beverages', 'Billing'];
    
    zonesList.forEach(zone => {
        const visits = zoneVisits[zone].visits;
        const dwell = zoneVisits[zone].avgDwell;
        tableHtml += `
            <tr>
                <td><strong style="color:var(--text-primary); font-weight:600;">${zone}</strong></td>
                <td class="text-center">${visits}</td>
                <td class="text-center"><span class="badge-custom">${dwell}s</span></td>
            </tr>
        `;
    });
    tableBody.innerHTML = tableHtml;

    // Refresh charts data values dynamically
    if (hourlyChartInstance && zoneChartInstance) {
        // Update zone values
        zoneChartInstance.data.datasets[0].data = zonesList.map(z => zoneVisits[z].visits);
        zoneChartInstance.update();
        
        // Update hourly values
        hourlyChartInstance.data.datasets[0].data = Object.values(hourlyVisits);
        hourlyChartInstance.update();
    }
}

// Reset heatmap operations
function resetHeatmapData() {
    heatmapPoints = [];
    addAlert("Database heatmap coordinates reset by user.");
}

// Resets metrics simulation (Admin only)
function clearDatabase() {
    if (confirm("Clear metrics logs? This will reset all visits counts and history.")) {
        simulatedCustomers = [];
        activeAlerts = [];
        heatmapPoints = [];
        totalVisitorsCount = 0;
        totalDwellTime = 0;
        
        for (let z in zoneVisits) {
            zoneVisits[z].visits = 0;
        }
        for (let h in hourlyVisits) {
            hourlyVisits[h] = 0;
        }
        
        addAlert("Database fully cleared. Fresh metrics loop started.");
        updateStatsUI();
    }
}

// Session Logouts
function handleLogout() {
    localStorage.clear();
    window.location.href = 'index.html';
}
