/**
 * admin-charts.js — Chart.js initialization for Admin executive overview.
 */
function initAdminOverviewCharts(weeklyLabels, weeklyData, concernLabels, concernData) {
    const trendEl = document.getElementById('weeklyTrendChart');
    const donutEl = document.getElementById('concernDonutChart');

    if (trendEl && window.Chart) {
        new Chart(trendEl.getContext('2d'), {
            type: 'bar',
            data: {
                labels: weeklyLabels,
                datasets: [{
                    label: 'Appointments',
                    data: weeklyData,
                    backgroundColor: '#2563eb',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });
    }

    if (donutEl && window.Chart) {
        new Chart(donutEl.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: concernLabels,
                datasets: [{
                    data: concernData,
                    backgroundColor: ['#2563eb', '#7c3aed', '#ea580c', '#db2777', '#64748b']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }
}
