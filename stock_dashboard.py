import yfinance as yf
import pandas as pd
import numpy as np
import schedule
import time
import datetime
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
import os

# 定義股票代碼與名稱
tickers = {
    '^TWII': '台股大盤',
    '2330.TW': '台積電',
    '0050.TW': '元大台灣50'
}

# 抓取前一天收盤數據與融資融券
def fetch_daily_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="2d")
    if len(hist) < 2:
        return None
    last_day = hist.iloc[-1]
    prev_day = hist.iloc[-2]
    return {
        'close': last_day['Close'],
        'volume': last_day['Volume'],
        'change': (last_day['Close'] - prev_day['Close']) / prev_day['Close'] * 100,
        'date': hist.index[-1].strftime('%Y-%m-%d')
    }

def fetch_margin_data(ticker):
    # TWSE 融資融券數據（簡化版，實際需爬蟲）
    url = f"https://www.twse.com.tw/zh/trading/margin/marginBalance.html?stockNo={ticker.split('.')[0]}"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        # 假設數據在表格中，實際需根據 TWSE 網站結構解析
        margin = "無法即時抓取，需手動查詢 TWSE"
        return margin
    except:
        return "無法抓取融資融券數據"

# 蒙特卡羅模擬計算漲跌機率與預測價位
def monte_carlo_simulation(ticker, current_price, days=1, simulations=1000):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y")
    returns = hist['Close'].pct_change().dropna()
    mean_return = returns.mean()
    std_return = returns.std()
    
    # 模擬未來一天的價格路徑
    sim_prices = []
    for _ in range(simulations):
        price_path = current_price * (1 + np.random.normal(mean_return, std_return, days))
        sim_prices.append(price_path[-1])
    
    # 計算漲跌機率與預測價位區間
    sim_prices = np.array(sim_prices)
    up_prob = len(sim_prices[sim_prices > current_price]) / simulations * 100
    down_prob = 100 - up_prob
    pred_price = np.mean(sim_prices)
    conf_interval = np.percentile(sim_prices, [5, 95])  # 90% 信賴區間
    return up_prob, down_prob, pred_price, conf_interval

# 技術指標計算（布林通道與 RSI）
def technical_indicators(ticker, current_price):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="20d")
    sma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
    std20 = hist['Close'].rolling(window=20).std().iloc[-1]
    bb_upper = sma20 + 2 * std20  # 布林通道上軌
    bb_lower = sma20 - 2 * std20  # 布林通道下軌
    
    # RSI 計算
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean().iloc[-1]
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().iloc[-1]
    rs = gain / loss if loss != 0 else np.inf
    rsi = 100 - (100 / (1 + rs))
    
    # 做空/做多點位
    long_point = bb_lower if rsi < 30 else None  # 超賣，建議做多
    short_point = bb_upper if rsi > 70 else None  # 超買，建議做空
    return sma20, bb_upper, bb_lower, rsi, long_point, short_point

# 生成 HTML 儀表板
def generate_dashboard(data, intraday=False):
    date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>台股即時分析儀表板</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            th {{ background-color: #f2f2f2; }}
            h1 {{ text-align: center; }}
        </style>
    </head>
    <body>
        <h1>台股即時分析儀表板 - {date_str}</h1>
        <table>
            <tr>
                <th>股票</th>
                <th>收盤價</th>
                <th>成交量</th>
                <th>漲跌幅 (%)</th>
                <th>融資融券</th>
                <th>上漲機率 (%)</th>
                <th>下跌機率 (%)</th>
                <th>預測價位</th>
                <th>預測區間 (90%)</th>
                <th>SMA20</th>
                <th>布林上軌</th>
                <th>布林下軌</th>
                <th>RSI</th>
                <th>做多點位</th>
                <th>做空點位</th>
            </tr>
    """
    
    for ticker, name in tickers.items():
        if ticker in data:
            d = data[ticker]
            html_content += f"""
            <tr>
                <td>{name}</td>
                <td>{d['close']:.2f}</td>
                <td>{d['volume']:,.0f}</td>
                <td>{d['change']:.2f}</td>
                <td>{d['margin']}</td>
                <td>{d['up_prob']:.2f}</td>
                <td>{d['down_prob']:.2f}</td>
                <td>{d['pred_price']:.2f}</td>
                <td>{d['conf_interval'][0]:.2f} - {d['conf_interval'][1]:.2f}</td>
                <td>{d['sma20']:.2f}</td>
                <td>{d['bb_upper']:.2f}</td>
                <td>{d['bb_lower']:.2f}</td>
                <td>{d['rsi']:.2f}</td>
                <td>{d['long_point']:.2f if d['long_point'] else '無'}</td>
                <td>{d['short_point']:.2f if d['short_point'] else '無'}</td>
            </tr>
            """
    
    html_content += """
        </table>
    </body>
    </html>
    """
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

# 主分析函數
def analyze_stocks():
    data = {}
    for ticker, name in tickers.items():
        daily_data = fetch_daily_data(ticker)
        if daily_data:
            up_prob, down_prob, pred_price, conf_interval = monte_carlo_simulation(ticker, daily_data['close'])
            sma20, bb_upper, bb_lower, rsi, long_point, short_point = technical_indicators(ticker, daily_data['close'])
            data[ticker] = {
                'close': daily_data['close'],
                'volume': daily_data['volume'],
                'change': daily_data['change'],
                'margin': fetch_margin_data(ticker),
                'up_prob': up_prob,
                'down_prob': down_prob,
                'pred_price': pred_price,
                'conf_interval': conf_interval,
                'sma20': sma20,
                'bb_upper': bb_upper,
                'bb_lower': bb_lower,
                'rsi': rsi,
                'long_point': long_point,
                'short_point': short_point
            }
    generate_dashboard(data)

# 即時更新函數（開盤後每10分鐘）
def intraday_update():
    data = {}
    for ticker, name in tickers.items():
        stock = yf.Ticker(ticker)
        current = stock.history(period="1d")
        if not current.empty:
            current_price = current['Close'].iloc[-1]
            current_volume = current['Volume'].iloc[-1]
            prev_close = fetch_daily_data(ticker)['close']
            change = (current_price - prev_close) / prev_close * 100
            up_prob, down_prob, pred_price, conf_interval = monte_carlo_simulation(ticker, current_price)
            sma20, bb_upper, bb_lower, rsi, long_point, short_point = technical_indicators(ticker, current_price)
            data[ticker] = {
                'close': current_price,
                'volume': current_volume,
                'change': change,
                'margin': fetch_margin_data(ticker),
                'up_prob': up_prob,
                'down_prob': down_prob,
                'pred_price': pred_price,
                'conf_interval': conf_interval,
                'sma20': sma20,
                'bb_upper': bb_upper,
                'bb_lower': bb_lower,
                'rsi': rsi,
                'long_point': long_point,
                'short_point': short_point
            }
    generate_dashboard(data, intraday=True)

# 排程設定
schedule.every().day.at("08:30").do(analyze_stocks)
schedule.every(10).minutes.between("09:00", "13:30").do(intraday_update)

# 主程式
while True:
    schedule.run_pending()
    time.sleep(60)