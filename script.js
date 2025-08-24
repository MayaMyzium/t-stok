/*
 * script.js
 *
 * This script fetches the latest prediction JSON and draws simple
 * doughnut charts using Chart.js to visualise the probability that a
 * stock or index will rise on the next trading day.  It also updates
 * textual price range information below each chart.
 */

async function loadPredictions() {
    try {
        const resp = await fetch('data/latest_predictions.json');
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        const result = await resp.json();
        const predictions = result.predictions;
        // Mapping of keys to DOM id suffixes
        const mapping = {
            'TaiwanIndex': 'twindex',
            '2330': '2330',
            '0050': '0050'
        };
        for (const key in mapping) {
            if (!predictions.hasOwnProperty(key)) continue;
            const data = predictions[key];
            const suffix = mapping[key];
            renderChart(suffix, data);
        }
    } catch (err) {
        console.error('Failed to load predictions:', err);
    }
}

function renderChart(idSuffix, data) {
    const canvasId = `chart-${idSuffix}`;
    const rangeId = `range-${idSuffix}`;
    const ctx = document.getElementById(canvasId).getContext('2d');
    const probUp = data.prob_up;
    const probDown = data.prob_down;
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['下跌機率', '上漲機率'],
            datasets: [{
                data: [probDown, probUp],
                backgroundColor: ['#e74c3c', '#2ecc71'],
                hoverBackgroundColor: ['#c0392b', '#27ae60'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const label = ctx.label || '';
                            const value = ctx.parsed * 100;
                            return `${label}: ${value.toFixed(1)}%`;
                        }
                    }
                },
                title: {
                    display: false
                }
            }
        }
    });
    // Update price range text
    const priceStr = `預估價格：${data.pred_price} (區間 ${data.pred_low} – ${data.pred_high})`;
    const rangeElem = document.getElementById(rangeId);
    rangeElem.textContent = priceStr;
}

// Trigger data loading after DOM content is ready
document.addEventListener('DOMContentLoaded', loadPredictions);