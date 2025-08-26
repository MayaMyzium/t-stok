// 主程式：載入後執行
document.addEventListener('DOMContentLoaded', () => {
  updateFearGreed();
  updateBTC();
  updateCryptos();
  // 週期更新
  setInterval(updateFearGreed, 60 * 60 * 1000); // 每小時更新一次
  setInterval(updateBTC, 60 * 60 * 1000);
  setInterval(updateCryptos, 15 * 60 * 1000); // 每15分鐘更新一次
});

/**
 * 取得恐懼貪婪指數
 * 參考 alternative.me 的 API【500990096785158†L220-L244】
 */
async function updateFearGreed() {
  const valueEl = document.getElementById('fng-value');
  const classEl = document.getElementById('fng-class');
  const updateEl = document.getElementById('fng-update');
  try {
    const res = await fetch('https://api.alternative.me/fng/?limit=1&format=json');
    const json = await res.json();
    if (json && json.data && json.data.length > 0) {
      const fng = json.data[0];
      valueEl.textContent = fng.value;
      classEl.textContent = fng.value_classification;
      // 計算下一次更新時間（秒轉成時分秒）
      if (fng.time_until_update) {
        const secs = parseInt(fng.time_until_update, 10);
        const hours = Math.floor(secs / 3600);
        const minutes = Math.floor((secs % 3600) / 60);
        const seconds = secs % 60;
        updateEl.textContent = `距離下次更新：${hours} 小時 ${minutes} 分 ${seconds} 秒`;
      } else {
        updateEl.textContent = '';
      }
    } else {
      valueEl.textContent = '--';
      classEl.textContent = '無法取得資料';
    }
  } catch (e) {
    console.error('取得恐懼貪婪指數失敗', e);
    valueEl.textContent = '--';
    classEl.textContent = '載入失敗';
    updateEl.textContent = '';
  }
}

/**
 * 更新比特幣地址餘額與繪製近三個月變化圖表
 * 使用 blockchain.info 的 rawaddr 端點【736105284045409†L117-L137】
 */
async function updateBTC() {
  const address = document.getElementById('btc-address').textContent;
  const balanceEl = document.getElementById('btc-balance');
  try {
    // 加上 cors=true 以啟用 CORS【736105284045409†L18-L21】
    const url = `https://blockchain.info/rawaddr/${address}?limit=1000&cors=true`;
    const res = await fetch(url);
    const data = await res.json();
    // final_balance 為 satoshi；轉成 BTC
    const finalBalanceBTC = data.final_balance / 1e8;
    balanceEl.textContent = finalBalanceBTC.toFixed(8);
    const txs = data.txs || [];
    const chartData = computeBTCBalances(txs, finalBalanceBTC);
    drawBTCChart(chartData.labels, chartData.data);
  } catch (e) {
    console.error('取得比特幣地址資料失敗', e);
    balanceEl.textContent = '--';
  }
}

/**
 * 計算每日餘額序列。
 * @param {Array} txs 交易列表
 * @param {number} finalBalance 最終餘額（BTC）
 * @returns {{labels: string[], data: number[]}}
 */
function computeBTCBalances(txs, finalBalance) {
  const targetDays = 90; // 最近三個月 (約90天)
  const now = new Date();
  const endDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const netMap = {};
  // 計算每筆交易對該地址的淨值 (正為存入，負為轉出)
  for (const tx of txs) {
    const tsDate = new Date(tx.time * 1000);
    const dayStr = formatDate(tsDate);
    let net = 0;
    // outputs
    if (Array.isArray(tx.out)) {
      for (const o of tx.out) {
        if (o.addr === document.getElementById('btc-address').textContent) {
          net += o.value;
        }
      }
    }
    // inputs
    if (Array.isArray(tx.inputs)) {
      for (const i of tx.inputs) {
        if (i.prev_out && i.prev_out.addr === document.getElementById('btc-address').textContent) {
          net -= i.prev_out.value;
        }
      }
    }
    if (!netMap[dayStr]) netMap[dayStr] = 0;
    netMap[dayStr] += net;
  }
  const labels = [];
  const data = [];
  let currentBalance = finalBalance;
  // 從最新日期倒推到 targetDays 之前
  for (let i = 0; i < targetDays; i++) {
    const date = new Date(endDate);
    date.setDate(endDate.getDate() - i);
    const dayStr = formatDate(date);
    // 將當前餘額塞入陣列頭部，使圖表從舊到新
    labels.unshift(dayStr);
    data.unshift(parseFloat(currentBalance.toFixed(8)));
    // 下個迭代日需要減去當天的淨流入 (因為從最後往前推)
    if (netMap[dayStr]) {
      currentBalance -= netMap[dayStr] / 1e8;
    }
  }
  return { labels, data };
}

/**
 * 格式化日期為 YYYY-MM-DD
 */
function formatDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

let btcChart;
function drawBTCChart(labels, data) {
  const ctx = document.getElementById('btcChart').getContext('2d');
  if (btcChart) {
    btcChart.data.labels = labels;
    btcChart.data.datasets[0].data = data;
    btcChart.update();
    return;
  }
  btcChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'BTC 餘額',
          data: data,
          borderColor: '#3498db',
          backgroundColor: 'rgba(52,152,219,0.2)',
          tension: 0.1,
          fill: true,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          ticks: {
            maxTicksLimit: 5,
            maxRotation: 0,
            minRotation: 0
          }
        },
        y: {
          beginAtZero: true
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.parsed.y} BTC`
          }
        }
      }
    }
  });
}

/**
 * 更新多幣種即時價格與 RSI 指標
 * 利用 coingecko 的市場圖表資料計算 RSI
 */
async function updateCryptos() {
  const coins = [
    { id: 'bitcoin', symbol: 'BTC', name: '比特幣' },
    { id: 'ethereum', symbol: 'ETH', name: '以太幣' },
    { id: 'ripple', symbol: 'XRP', name: 'XRP' },
    { id: 'dogecoin', symbol: 'DOGE', name: '狗狗幣' },
    { id: 'cardano', symbol: 'ADA', name: 'ADA' },
    // 新增 Solana 幣種
    { id: 'solana', symbol: 'SOL', name: '索拉納' }
  ];
  const tbody = document.getElementById('crypto-tbody');
  tbody.innerHTML = '';
  for (const coin of coins) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${coin.name} (${coin.symbol})</td>
      <td id="price-${coin.id}">載入中…</td>
      <td id="rsi-${coin.id}">--</td>
      <td id="rec-${coin.id}"></td>
    `;
    tbody.appendChild(tr);
    updateCoinInfo(coin).catch((err) => {
      console.error('取得幣種資料失敗', coin.id, err);
      document.getElementById(`price-${coin.id}`).textContent = '無法取得資料';
    });
  }
}

async function updateCoinInfo(coin) {
  // 取得近 90 天日線資料
  const url = `https://api.coingecko.com/api/v3/coins/${coin.id}/market_chart?vs_currency=usd&days=90&interval=daily`;
  const res = await fetch(url);
  const data = await res.json();
  const prices = data.prices || [];
  if (prices.length === 0) throw new Error('無價格資料');
  // 取得最新價格
  const lastPrice = prices[prices.length - 1][1];
  document.getElementById(`price-${coin.id}`).textContent = `價格: $${lastPrice.toFixed(2)}`;
  // 計算 RSI（14日）
  const closes = prices.map((p) => p[1]);
  const rsiVal = calculateRSI(closes.slice(-15));
  document.getElementById(`rsi-${coin.id}`).textContent = `RSI: ${rsiVal.toFixed(2)}`;
  // 推薦買賣區間：RSI<30 偏買，>70 偏賣，其餘中立
  let rec = '';
  if (rsiVal < 30) rec = '偏買區';
  else if (rsiVal > 70) rec = '偏賣區';
  else rec = '中立區';
  document.getElementById(`rec-${coin.id}`).textContent = rec;
}

/**
 * 計算 RSI 指標
 * 公式：RSI = 100 - (100 / (1 + RS))，其中 RS = 平均漲幅 / 平均跌幅【500990096785158†L244-L274】
 * @param {number[]} closes 收盤價陣列（至少15筆）
 * @returns {number} RSI 值
 */
function calculateRSI(closes) {
  if (closes.length < 2) return 50;
  let gains = 0;
  let losses = 0;
  // 從第二筆開始比較
  for (let i = 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff > 0) gains += diff;
    else losses -= diff; // diff 為負值
  }
  const period = closes.length - 1;
  const avgGain = gains / period;
  const avgLoss = losses / period;
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  const rsi = 100 - 100 / (1 + rs);
  return rsi;
}