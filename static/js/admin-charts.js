/**
 * admin-charts.js — Enhanced Chart.js initialization for ConnectGuidance Admin Executive Overview.
 * Preserves the clean light palette with Admin Royal Purple (#7c3aed) theme.
 */

function initAdminOverviewCharts(weeklyLabels, weeklyData, concernLabels, concernData) {
    if (!window.Chart) {
        console.warn('Chart.js library is not loaded.');
        return;
    }

    // Default fallbacks if empty
    weeklyLabels = Array.isArray(weeklyLabels) && weeklyLabels.length ? weeklyLabels : ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 'Week 7', 'Week 8'];
    weeklyData = Array.isArray(weeklyData) && weeklyData.length ? weeklyData : [0, 0, 0, 0, 0, 0, 0, 0];
    
    // ── 1. Weekly Appointment Volume Trend (Bar Chart) ───────────────────────
    const trendEl = document.getElementById('weeklyTrendChart');
    if (trendEl) {
        // Destroy existing chart instance if any (e.g. re-init)
        if (window._cgTrendChartInstance) {
            window._cgTrendChartInstance.destroy();
        }

        const ctx = trendEl.getContext('2d');

        // Create gradient fill for the bars
        let barColor = '#7c3aed';
        try {
            const gradient = ctx.createLinearGradient(0, 0, 0, 260);
            gradient.addColorStop(0, 'rgba(124, 58, 237, 0.95)');
            gradient.addColorStop(1, 'rgba(99, 102, 241, 0.75)');
            barColor = gradient;
        } catch (e) {
            barColor = '#7c3aed';
        }

        window._cgTrendChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: weeklyLabels,
                datasets: [{
                    label: 'Sessions Scheduled',
                    data: weeklyData,
                    backgroundColor: barColor,
                    hoverBackgroundColor: '#6d28d9',
                    borderRadius: 8,
                    borderSkipped: false,
                    maxBarThickness: 38
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 750,
                    easing: 'easeOutQuart'
                },
                layout: {
                    padding: { top: 12, bottom: 4, left: 4, right: 4 }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        titleColor: '#ffffff',
                        bodyColor: '#cbd5e1',
                        padding: 10,
                        cornerRadius: 8,
                        titleFont: { size: 12, weight: '700' },
                        bodyFont: { size: 12 },
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                const val = context.raw || 0;
                                return `${val} ${val === 1 ? 'consultation' : 'consultations'}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false,
                            drawBorder: false
                        },
                        ticks: {
                            color: '#64748b',
                            font: { size: 11, weight: '600' }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#f1f5f9',
                            drawBorder: false
                        },
                        ticks: {
                            precision: 0,
                            color: '#94a3b8',
                            font: { size: 11 },
                            padding: 8
                        }
                    }
                }
            }
        });
    }

    // ── 2. Concern Distribution (Doughnut Chart) ─────────────────────────────
    const donutEl = document.getElementById('concernDonutChart');
    if (donutEl) {
        if (window._cgDonutChartInstance) {
            window._cgDonutChartInstance.destroy();
        }

        const totalConcerns = Array.isArray(concernData) ? concernData.reduce((a, b) => a + b, 0) : 0;
        const hasData = totalConcerns > 0 && Array.isArray(concernLabels) && concernLabels.length > 0;

        const effectiveLabels = hasData ? concernLabels : ['No Sessions Recorded'];
        const effectiveData = hasData ? concernData : [1];
        const effectiveColors = hasData 
            ? ['#7c3aed', '#3b82f6', '#0d9488', '#f59e0b', '#ec4899', '#6366f1', '#10b981', '#64748b']
            : ['#e2e8f0'];

        const ctx = donutEl.getContext('2d');
        window._cgDonutChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: effectiveLabels,
                datasets: [{
                    data: effectiveData,
                    backgroundColor: effectiveColors,
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '72%',
                animation: {
                    duration: 750,
                    easing: 'easeOutQuart'
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            boxHeight: 12,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 14,
                            color: '#475569',
                            font: { size: 11, weight: '600' }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        titleColor: '#ffffff',
                        bodyColor: '#cbd5e1',
                        padding: 10,
                        cornerRadius: 8,
                        titleFont: { size: 12, weight: '700' },
                        bodyFont: { size: 12 },
                        callbacks: {
                            label: function(context) {
                                if (!hasData) return 'No data available';
                                const val = context.raw || 0;
                                const pct = totalConcerns > 0 ? Math.round((val / totalConcerns) * 100) : 0;
                                return ` ${val} sessions (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}
