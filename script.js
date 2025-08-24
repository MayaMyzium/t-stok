/*
 * 主腳本：處理恐懼貪婪指數、比特幣地址餘額、價格與RSI、以及合約多空分析。
 * 本檔案假設在GitHub Pages等靜態環境執行，使用Fetch API呼叫外部服務。
 */

// 封裝等待工具
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// === 恐懼貪婪指數 ===
async function fetchFearGreed() {
    const fngValueEl = document.getElementById('fng-value');
    const fngImg = document.getElementById('fng-image');
    try {
        const res = await fetch('https://api.alternative.me/fng/?limit=1&format=json');
        if (!res.ok) throw new Error('Network response was not ok');
        const json = await res.json();
        const data = json && json.data && json.data[0];
        if (data) {
            const value = data.value;
            const classification = data.value_classification;
            fngValueEl.textContent = `${value} (${classification})`;
            // 隱藏備用圖片（若載入成功）
            fngImg.style.display = 'none';
        }
    } catch (err) {
        console.error('FNG API error', err);
        fngValueEl.textContent = '無法取得指數';
        // 失敗時顯示備用圖片
        fngImg.style.display = 'block';
    }
}

// === 比特幣地址餘額 ===
async function fetchAddressData(address) {
    // 取得單一地址的交易資料；只取前2000筆
    const url = `https://api.blockcypher.com/v1/btc/main/addrs/${address}?limit=2000`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('BlockCypher API error');
    const data = await res.json();
    const txrefs = data.txrefs || [];
    const dailyBalances = {};
    txrefs.forEach(tx => {
        if (!tx.confirmed) return;
        const date = tx.confirmed.slice(0, 10); // YYYY-MM-DD
        // 只記錄每日最後一筆ref_balance（資料由區塊高度排序）
        if (!(date in dailyBalances)) {
            dailyBalances[date] = tx.ref_balance / 1e8; // 轉為BTC
        }
    });
    const dates = Object.keys(dailyBalances).sort();
    const balances = dates.map(d => dailyBalances[d]);
    return { dates, balances };
}

async function renderAddressCharts() {
    const container = document.getElementById('address-charts');
    if (!container) return; // 只有在index頁面上存在
    // 提供地址與顯示名稱
    const addresses = [
        { addr: '1Ay8vMC7R1UbyCCZRVULMV7iQpHSAbguJP', label: '地址1: 1Ay8vM...' },
        { addr: '34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo', label: '地址2: 34xp4v...' },
        { addr: '3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6', label: '地址3: 3M219K...' },
        { addr: '3LQUu4v9z6KNch71j7kbj8GPeAGUo1FW6a', label: '地址4: 3LQUu4...' },
        { addr: '3FHNBLobJnbCTFTVakh5TXmEneyf5PT61B', label: '地址5: 3FHNBL...' },
        { addr: '1Pzaqw98PeRfyHypfqyEgg5yycJRsENrE7', label: '地址6: 1Pzaqw...' },
        { addr: '34HpHYiyQwg69gFmCq2BGHjF1DZnZnBeBP', label: '地址7: 34HpHY...' },
        { addr: 'bc1q7t9fxfaakmtk8pj7tdxjvwsng6y9x76czuaf5h', label: '地址8: bc1q7t...' }
    ];
    // 顧及某些地址交易數過多，本示例略過bc1qm34...(too large)
    const allDaily = {};
    for (const item of addresses) {
        try {
            const { dates, balances } = await fetchAddressData(item.addr);
            // 建立畫布
            const card = document.createElement('div');
            card.style.marginBottom = '20px';
            const title = document.createElement('h3');
            title.textContent = item.label;
            card.appendChild(title);
            const canvas = document.createElement('canvas');
            card.appendChild(canvas);
            container.appendChild(card);
            const ctx = canvas.getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [
                        {
                            label: 'BTC餘額 (BTC)',
                            data: balances,
                            fill: false,
                            borderColor: 'rgba(75,192,192,1)',
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'month',
                                displayFormats: {
                                    month: 'yyyy-MM'
                                }
                            },
                            title: {
                                display: true,
                                text: '日期'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: '餘額 (BTC)'
                            }
                        }
                    }
                }
            });
            // 收集要聚合的地址（去除前兩個地址）
            if (addresses.indexOf(item) >= 2) {
                dates.forEach((d, idx) => {
                    if (!allDaily[d]) allDaily[d] = 0;
                    allDaily[d] += balances[idx];
                });
            }
        } catch (err) {
            console.error('Address fetch error', err);
            const p = document.createElement('p');
            p.textContent = `${item.label} 無法取得資料。`;
            container.appendChild(p);
        }
        // 稍微等待，以免過多請求
        await sleep(500);
    }
    // 繪製總和折線圖
    if (Object.keys(allDaily).length > 0) {
        const sortedDates = Object.keys(allDaily).sort();
        const sums = sortedDates.map(d => allDaily[d]);
        const card = document.createElement('div');
        const title = document.createElement('h3');
        title.textContent = '地址3-8總和餘額變化';
        card.appendChild(title);
        const canvas = document.createElement('canvas');
        card.appendChild(canvas);
        container.appendChild(card);
        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedDates,
                datasets: [
                    {
                        label: '總餘額 (BTC)',
                        data: sums,
                        fill: false,
                        borderColor: 'rgba(255,99,132,1)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month',
                            displayFormats: {
                                month: 'yyyy-MM'
                            }
                        },
                        title: {
                            display: true,
                            text: '日期'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: '餘額 (BTC)'
                        }
                    }
                }
            }
        });
    }
}

// === RSI & Price ===
function computeRSI(closes, period = 14) {
    if (closes.length < period + 1) return null;
    let gains = 0;
    let losses = 0;
    for (let i = 1; i <= period; i++) {
        const change = closes[i] - closes[i - 1];
        if (change > 0) gains += change;
        else losses += -change;
    }
    let avgGain = gains / period;
    let avgLoss = losses / period;
    // 避免除以零
    if (avgLoss === 0) return 100;
    const rs = avgGain / avgLoss;
    return 100 - 100 / (1 + rs);
}

async function fetchPricesAndRsi() {
    const tableBody = document.querySelector('#price-table tbody');
    if (!tableBody) return;
    const coins = [
        { symbol: 'BTCUSDT', name: 'BTC' },
        { symbol: 'ETHUSDT', name: 'ETH' },
        { symbol: 'XRPUSDT', name: 'XRP' },
        { symbol: 'DOGEUSDT', name: 'DOGE' },
        { symbol: 'ADAUSDT', name: 'ADA' }
    ];
    for (const coin of coins) {
        try {
            // 取得最近100日K線，計算收盤價及RSI
            const klinesUrl = `https://api.binance.com/api/v3/klines?symbol=${coin.symbol}&interval=1d&limit=100`;
            const res = await fetch(klinesUrl);
            const klines = await res.json();
            // 收盤價在索引4
            const closes = klines.map(k => parseFloat(k[4]));
            const lastPrice = closes[closes.length - 1];
            const rsi = computeRSI(closes.slice(-15));
            let suggestion = '中性';
            if (rsi !== null) {
                if (rsi >= 70) suggestion = '可能過熱，考慮減倉';
                else if (rsi <= 30) suggestion = '可能超賣，考慮布局';
            }
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${coin.name}</td>
                <td>${lastPrice.toFixed(2)}</td>
                <td>${rsi ? rsi.toFixed(2) : 'N/A'}</td>
                <td>${suggestion}</td>
            `;
            tableBody.appendChild(row);
        } catch (err) {
            console.error('Price/RSI fetch error', err);
        }
        await sleep(300);
    }
}

// === Binance & OKX Long/Short Ratio (Analysis Page) ===
async function fetchLongShortAnalysis() {
    const longShortSection = document.getElementById('long-short-analysis');
    if (!longShortSection) return; // 只在analysis頁面執行
    const coins = [
        { symbol: 'BTCUSDT', name: 'BTC' },
        { symbol: 'ETHUSDT', name: 'ETH' },
        { symbol: 'XRPUSDT', name: 'XRP' },
        { symbol: 'DOGEUSDT', name: 'DOGE' },
        { symbol: 'ADAUSDT', name: 'ADA' }
    ];
    const table = document.createElement('table');
    table.innerHTML = `
        <thead><tr><th>幣種</th><th>Binance 多空比</th><th>分析</th></tr></thead>
        <tbody></tbody>
    `;
    longShortSection.appendChild(table);
    const tbody = table.querySelector('tbody');
    for (const coin of coins) {
        try {
            // 取得最近24小時每小時多空比，period=1h, limit=24
            const url = `https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=${coin.symbol}&period=5m&limit=12`;
            const res = await fetch(url);
            const data = await res.json();
            // 取最新一筆
            const latest = data[data.length - 1];
            const ratio = latest.longShortRatio;
            let analysisText = '';
            const r = parseFloat(ratio);
            if (r > 1) {
                analysisText = '多頭略強';
            } else if (r < 1) {
                analysisText = '空頭略強';
            } else {
                analysisText = '多空平衡';
            }
            const row = document.createElement('tr');
            row.innerHTML = `<td>${coin.name}</td><td>${ratio}</td><td>${analysisText}</td>`;
            tbody.appendChild(row);
        } catch (err) {
            console.error('Long/short fetch error', err);
            const row = document.createElement('tr');
            row.innerHTML = `<td>${coin.name}</td><td colspan="2">無法取得資料</td>`;
            tbody.appendChild(row);
        }
        await sleep(300);
    }
    // 解釋性段落
    const para = document.createElement('p');
    para.textContent = '多空比率大於1表示多單佔比高，可能代表市場偏多；低於1則偏空。本分析依Binance永續合約資料，僅供參考。';
    longShortSection.appendChild(para);
}

// 主進入點
document.addEventListener('DOMContentLoaded', () => {
    fetchFearGreed();
    renderAddressCharts();
    fetchPricesAndRsi();
    fetchLongShortAnalysis();
});