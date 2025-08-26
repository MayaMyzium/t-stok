// taiwan_summary.js
// 在進一步分析頁面載入每日台股預測摘要

document.addEventListener('DOMContentLoaded', () => {
  const tbody = document.getElementById('taiwan-summary-body');
  if (!tbody) return;
  fetch('latest_predictions_taiwan.json')
    .then((res) => {
      if (!res.ok) throw new Error('無法載入台股預測資料');
      return res.json();
    })
    .then((data) => {
      tbody.innerHTML = '';
      const preds = data.predictions || {};
      const labels = {
        TaiwanIndex: '加權指數',
        '2330': '台積電(2330)',
        '0050': '元大台灣50(0050)'
      };
      for (const key of Object.keys(labels)) {
        const pred = preds[key];
        if (!pred) continue;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${labels[key]}</td>
          <td>${(pred.prob_up * 100).toFixed(1)}%</td>
          <td>${(pred.prob_down * 100).toFixed(1)}%</td>
          <td>${pred.pred_price.toFixed(2)}</td>
          <td>${pred.pred_low.toFixed(2)} ~ ${pred.pred_high.toFixed(2)}</td>
          <td>${pred.entry_long.toFixed(2)}</td>
          <td>${pred.entry_short.toFixed(2)}</td>
        `;
        tbody.appendChild(tr);
      }
    })
    .catch((err) => {
      console.error('台股預測摘要載入錯誤', err);
      tbody.innerHTML = '<tr><td colspan="7">無法取得台股預測資料</td></tr>';
    });
});