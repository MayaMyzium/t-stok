// taiwan.js
// 讀取 daily 和 intraday JSON，填入表格

function loadDaily() {
    // 讀取根目錄的 latest_predictions_taiwan.json（無 data 目錄）
    fetch('./latest_predictions_taiwan.json')
        .then(res => res.json())
        .then(data => {
            const tbody = document.querySelector('#daily-table tbody');
            tbody.innerHTML = '';
            const preds = data.predictions || {};
            const labels = {
                'TaiwanIndex': '加權指數',
                '2330': '台積電(2330)',
                '0050': '元大台灣50(0050)'
            };
            Object.keys(labels).forEach(key => {
                const pred = preds[key];
                if (!pred) return;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${labels[key]}</td>
                    <td>${(pred.prob_up * 100).toFixed(1)}%</td>
                    <td>${(pred.prob_down * 100).toFixed(1)}%</td>
                    <td>${pred.pred_price.toFixed(2)}</td>
                    <td>${pred.pred_low.toFixed(2)} ~ ${pred.pred_high.toFixed(2)}</td>
                    <td>${pred.entry_long.toFixed(2)}</td>
                    <td>${pred.entry_short.toFixed(2)}</td>
                `;
                tbody.appendChild(row);
            });
        })
        .catch(err => {
            console.error('Error loading daily predictions:', err);
        });
}

function loadRealtime() {
    // 讀取根目錄的 realtime_taiwan.json（無 data 目錄）
    fetch('./realtime_taiwan.json')
        .then(res => res.json())
        .then(data => {
            const tbody = document.querySelector('#realtime-table tbody');
            tbody.innerHTML = '';
            const updateTimeEl = document.getElementById('update-time');
            updateTimeEl.textContent = `更新時間：${new Date().toLocaleString('zh-TW')}`;
            const realtime = data.realtime || {};
            const labels = {
                'TaiwanIndex': '加權指數',
                '2330': '台積電(2330)',
                '0050': '元大台灣50(0050)'
            };
            Object.keys(labels).forEach(key => {
                const r = realtime[key];
                if (!r) return;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${labels[key]}</td>
                    <td>${r.last_price.toFixed(2)}</td>
                    <td>${r.pct_change.toFixed(2)}</td>
                `;
                tbody.appendChild(row);
            });
        })
        .catch(err => {
            console.error('Error loading realtime data:', err);
        });
}

document.addEventListener('DOMContentLoaded', () => {
    loadDaily();
    loadRealtime();
    // 每 10 分鐘更新一次即時資料
    setInterval(loadRealtime, 10 * 60 * 1000);
});