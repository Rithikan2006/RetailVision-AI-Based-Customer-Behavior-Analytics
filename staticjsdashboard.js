let hourlyChartInstance = null;
let zoneChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    fetchAnalytics();
    setInterval(fetchAnalytics, 2000);
});

function initCharts() {
    const ctxHourly = document.getElementById('hourlyChart').getContext('2d');
    hourlyChartInstance = new Chart(ctxHourly, {
        type: 'line',
        data: {
            labels: Array.from({length: 24}, (_, i) => `${i.toString().padStart(2, '0')}:00`),
            datasets: [{
                label: 'Visitors',
                data: Array(24).fill(0),
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
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: { color: '#94a3b8', font: { size: 9 } }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94a3b8', stepSize: 5 },
                    beginAtZero: true
                }
            }
        }
    });

    const ctxZone = document.getElementById('zoneChart').getContext('2d');
    zoneChartInstance = new Chart(ctxZone, {
        type: 'bar',
        data: {
            labels: ['Vegetables', 'Snacks', 'Beverages', 'Billing'],
            datasets: [{
                label: 'Unique Visits',
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.75)',
                    'rgba(59, 130, 246, 0.75)',
                    'rgba(6, 182, 212, 0.75)',
                    'rgba(249, 115, 22, 0.75)'
                ],
                borderWidth: 0,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94a3b8', precision: 0 },
                    beginAtZero: true
                }
            }
        }
    });
}

function fetchAnalytics() {
    fetch('/api/analytics')
        .then(response => response.json())
        .then(data => {
            updateKPIs(data);
            updateAlerts(data.alerts);
            updateCharts(data.hourly_chart, data.zone_chart);
            updateZoneTable(data.zone_chart);
        })
        .catch(error => console.error("Error fetching analytics:", error));
}

function updateKPIs(data) {
    document.getElementById('kpi-total').textContent = data.total_visitors;
    document.getElementById('kpi-current').textContent = data.current_visitors;
    document.getElementById('kpi-dwell').textContent = data.average_stay_time;
    document.getElementById('kpi-peak').textContent = data.peak_hour;
}

function updateAlerts(alerts) {
    const container = document.getElementById('alerts-container');
    const indicator = document.getElementById('alert-indicator');
    
    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<div class="text-center py-4 text-muted" style="font-size:0.85rem;">No active alerts. Everything normal.</div>';
        indicator.className = "badge bg-success";
        indicator.textContent = "Normal";
        return;
    }
    
    const hasCritical = alerts.some(a => a.message.includes('ALERT'));
    if (hasCritical) {
        indicator.className = "badge bg-danger animate-pulse";
        indicator.textContent = "Alert Active";
    } else {
        indicator.className = "badge bg-primary";
        indicator.textContent = "Monitoring";
    }
    
    let html = '';
    const reversed = [...alerts].reverse();
    reversed.forEach(alert => {
        const isCritical = alert.message.includes('ALERT');
        const isExit = alert.message.includes('exited');
        const isEntry = alert.message.includes('entered');
        
        let alertClass = '';
        if (isCritical) alertClass = 'alert-danger';
        else if (isExit) alertClass = 'alert-warning';
        else if (isEntry) alertClass = '';
        
        html += `
            <div class="alert-item ${alertClass}">
                <div class="alert-time">${alert.time}</div>
                <div>${alert.message}</div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function updateCharts(hourlyData, zoneData) {
    if (hourlyChartInstance && hourlyData) {
        const labels = Object.keys(hourlyData);
        const values = Object.values(hourlyData);
        hourlyChartInstance.data.labels = labels;
        hourlyChartInstance.data.datasets[0].data = values;
        hourlyChartInstance.update();
    }

    if (zoneChartInstance && zoneData) {
        const zones = ['Vegetables', 'Snacks', 'Beverages', 'Billing'];
        const values = zones.map(z => zoneData[z] ? zoneData[z].visits : 0);
        zoneChartInstance.data.datasets[0].data = values;
        zoneChartInstance.update();
    }
}

function updateZoneTable(zoneData) {
    const tableBody = document.getElementById('zone-table-body');
    if (!zoneData) return;
    
    const zones = ['Vegetables', 'Snacks', 'Beverages', 'Billing'];
    let html = '';
    
    zones.forEach(zone => {
        const visits = zoneData[zone] ? zoneData[zone].visits : 0;
        const dwell = zoneData[zone] ? zoneData[zone].avg_dwell : 0;
        html += `
            <tr>
                <td><strong style="color:var(--text-primary); font-weight:600;">${zone}</strong></td>
                <td class="text-center">${visits}</td>
                <td class="text-center"><span class="badge bg-secondary-custom">${dwell}s</span></td>
            </tr>
        `;
    });
    tableBody.innerHTML = html;
}

function changeVideoSource(source) {
    fetch(`/api/change_source?source=${source}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log(`Video source changed to: ${source}`);
                const feed = document.getElementById('video-feed');
                feed.src = `/video_feed?t=${Date.now()}`;
            }
        });
}

function refreshHeatmap() {
    fetch('/api/refresh_heatmap')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const img = document.getElementById('heatmap-img');
                img.src = `/static/heatmap.png?t=${Date.now()}`;
                console.log("Heatmap updated.");
            }
        });
}

function clearDatabase() {
    if (confirm("Are you sure you want to reset the analytics database? This will clear all tracked customer entries, movements, and heatmaps.")) {
        fetch('/api/clear_db', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert("Database reset successfully.");
                    location.reload();
                }
            });
    }
}