// ==========================================================================
// AI Attendance System - Dashboard Analytics & Live Feed
// ==========================================================================

let trendChartInstance = null;
let deptChartInstance = null;

async function fetchDashboardData() {
    try {
        const res = await fetch('/api/attendance/stats');
        const data = await res.json();
        if (data.success && data.stats) {
            updateStatsCards(data.stats);
            renderTrendChart(data.stats.trend || []);
            renderDeptChart(data.stats.dept_breakdown || []);
        }
    } catch (e) {
        console.error("Failed to load dashboard metrics:", e);
    }
}

function updateStatsCards(stats) {
    document.getElementById("stat-total-students").textContent = stats.total_students || 0;
    document.getElementById("stat-today-present").textContent = stats.today_present || 0;
    document.getElementById("stat-today-late").textContent = stats.today_late || 0;
    document.getElementById("stat-rate").textContent = (stats.attendance_rate || 0) + "%";
}

function renderTrendChart(trendData) {
    const ctx = document.getElementById("trendChart");
    if (!ctx) return;

    const labels = trendData.length ? trendData.map(d => d.date) : ["No Data"];
    const values = trendData.length ? trendData.map(d => d.count) : [0];

    if (trendChartInstance) {
        trendChartInstance.destroy();
    }

    trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Present Students',
                data: values,
                borderColor: '#3B82F6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2.5,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: '#3B82F6',
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: '#94A3B8' },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                },
                x: {
                    ticks: { color: '#94A3B8' },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                }
            }
        }
    });
}

function renderDeptChart(deptData) {
    const ctx = document.getElementById("deptChart");
    if (!ctx) return;

    const labels = deptData.length ? deptData.map(d => d.department) : ["No Attendance Yet"];
    const values = deptData.length ? deptData.map(d => d.count) : [1];
    const colors = deptData.length ? [
        '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4'
    ] : ['#334155'];

    if (deptChartInstance) {
        deptChartInstance.destroy();
    }

    deptChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94A3B8', boxWidth: 12, padding: 15 }
                }
            },
            cutout: '70%'
        }
    });
}

async function fetchTodayFeed() {
    const today = new Date().toISOString().split('T')[0];
    try {
        const res = await fetch(`/api/attendance/history?date=${today}&limit=20`);
        const data = await res.json();
        const tbody = document.getElementById("today-feed-body");
        if (!tbody) return;

        if (data.success && data.records && data.records.length > 0) {
            tbody.innerHTML = data.records.map(r => {
                const isPresent = r.status === 'Present';
                const statusBadge = isPresent
                    ? `<span class="badge badge-present">Present</span>`
                    : `<span class="badge badge-late">Late</span>`;
                const conf = (parseFloat(r.confidence || 1.0) * 100).toFixed(0);

                return `
                    <tr>
                        <td style="font-weight: 600; font-family: monospace;">${r.time}</td>
                        <td><span style="font-family: monospace; font-weight: 600; color: #60A5FA;">${r.student_id}</span></td>
                        <td style="font-weight: 600;">${r.student_name}</td>
                        <td><span class="badge badge-info">${r.department}</span></td>
                        <td>${statusBadge}</td>
                        <td><span style="font-weight: 600;">${conf}%</span></td>
                        <td style="color: var(--text-subtle);">${r.method || 'AI Face'}</td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--text-subtle);">
                        No attendance recorded yet today. Launch the Live Scanner to start scanning!
                    </td>
                </tr>
            `;
        }
    } catch (e) {
        console.error("Failed to load today feed:", e);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    fetchDashboardData();
    fetchTodayFeed();

    const refreshBtn = document.getElementById("btn-refresh-feed");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            fetchDashboardData();
            fetchTodayFeed();
            showToast("Dashboard refreshed", "info", 2000);
        });
    }

    // Auto-refresh feed and stats every 10 seconds
    setInterval(() => {
        fetchDashboardData();
        fetchTodayFeed();
    }, 10000);
});
