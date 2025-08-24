"""
advanced_analysis.py
====================

本模組提供一個函式 `compute_signals`，可依照改良後的多空比交易公式計算指標分數與自適應點位。函式將從
價格、成交量與多空比（LSR）資料計算穩健化的 z 分數、綜合信號、分位門檻以及進出場點位。

使用範例：

```python
import pandas as pd
from advanced_analysis import compute_signals

# 假設您已有包含時間、open、high、low、close、volume、lsr 欄位的 DataFrame df
signals = compute_signals(
    price=df['close'].values,
    high=df['high'].values,
    low=df['low'].values,
    lsr=df['lsr'].values,
    volume=df['volume'].values,
    n=48,
    m=1000,
    alpha=0.55,
    beta=0.35,
    gamma=0.10,
    eta=0.25,
    q_lo=0.20,
    q_hi=0.80,
    c=0.3,
    k_sl=1.5,
    k_tp=2.0,
    risk_pct=0.0075,
    point_value=1.0,
    ema_fast=21,
    ema_slow=55
)

# signals 是一個 DataFrame，其中包含 S, S* 與交易點位
print(signals.tail())
```

您可以自行調整參數，例如 n、m、alpha、beta、gamma 等，以適應不同週期或商品。
建議在小時線或 15 分資料上使用，並使用至少 1000 根歷史資料作為分位數參考。

注意：此程式僅作為學術研究用途，請勿依此進行真實交易。
"""

import numpy as np
import pandas as pd


def winsorize(x: np.ndarray, p: float = 0.05) -> np.ndarray:
    """Winsorize 統計方法：將序列中前後 p 百分比的極端值裁剪為指定分位數。"""
    lo, hi = np.nanquantile(x, [p, 1 - p])
    return np.clip(x, lo, hi)


def rolling_z(x: pd.Series, n: int) -> pd.Series:
    """計算滾動 z 分數。"""
    ma = x.rolling(n).mean()
    sd = x.rolling(n).std(ddof=0)
    return (x - ma) / sd


def ema(x: pd.Series, n: int) -> pd.Series:
    """計算指數加權移動平均 (EMA)。"""
    return pd.Series(x).ewm(span=n, adjust=False).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """計算平均真實波動 (ATR)。"""
    h, l, c = pd.Series(high), pd.Series(low), pd.Series(close)
    tr = pd.concat([
        (h - l),
        (h - c.shift(1)).abs(),
        (l - c.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def compute_signals(
    price: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    lsr: np.ndarray,
    volume: np.ndarray,
    n: int = 48,
    m: int = 1000,
    alpha: float = 0.55,
    beta: float = 0.35,
    gamma: float = 0.10,
    eta: float = 0.25,
    q_lo: float = 0.20,
    q_hi: float = 0.80,
    c: float = 0.3,
    k_sl: float = 1.5,
    k_tp: float = 2.0,
    risk_pct: float = 0.0075,
    point_value: float = 1.0,
    ema_fast: int = 21,
    ema_slow: int = 55
) -> pd.DataFrame:
    """根據改良後的公式計算指標分數與交易點位。

    Parameters
    ----------
    price : np.ndarray
        收盤價序列。
    high : np.ndarray
        最高價序列。
    low : np.ndarray
        最低價序列。
    lsr : np.ndarray
        多空比序列 (Long/Short Ratio)。
    volume : np.ndarray
        成交量序列。
    n : int
        計算滾動 z 分數的窗口大小。
    m : int
        計算歷史分位數的窗口大小。
    alpha, beta, gamma : float
        合成指標 S 的權重。
    eta : float
        量能放大係數。
    q_lo, q_hi : float
        做空與做多的門檻分位數。
    c, k_sl, k_tp : float
        進場與風控的 ATR 係數。
    risk_pct : float
        單筆風險佔帳戶資金百分比。
    point_value : float
        合約價值乘數（對於 USDT 計價合約通常為 1）。
    ema_fast, ema_slow : int
        趨勢過濾用的 EMA 周期。

    Returns
    -------
    pd.DataFrame
        包含綜合指標 S、S*、多空信號、進場價格、止損、追蹤停利與部位大小等欄位。
    """
    price = pd.Series(price, dtype=float)
    high = pd.Series(high, dtype=float)
    low = pd.Series(low, dtype=float)
    lsr = pd.Series(lsr, dtype=float)
    volume = pd.Series(volume, dtype=float)

    # 1) 穩健化與各項 z 分數
    lsr_w = pd.Series(winsorize(lsr.values))
    z_lsr = rolling_z(lsr_w, n)
    z_dlsr = rolling_z(lsr_w.diff(), n)
    momen = rolling_z(np.log(price).diff(), n)
    z_vol = rolling_z(volume, n).clip(lower=0.0)

    # 趨勢過濾 (EMA)
    trend = np.sign(ema(price, ema_fast) - ema(price, ema_slow))

    # 2) 綜合指標 S 與放大版 S*
    S = alpha * z_lsr + beta * z_dlsr + gamma * momen
    S_star = S * (1 + eta * z_vol) * ((S * trend) > 0)

    # 3) 使用歷史 m 期的分位數作為門檻
    rolling_ref = S_star.rolling(m, min_periods=int(m * 0.6))
    q_hi_series = rolling_ref.quantile(q_hi)
    q_lo_series = rolling_ref.quantile(q_lo)

    # 4) 多空信號判斷：再加上降噪條件（z 分數門檻與趨勢）
    long_cond = (S_star >= q_hi_series) & (z_lsr.abs() >= 0.8) & (z_dlsr.abs() >= 0.6) & (trend > 0)
    short_cond = (S_star <= q_lo_series) & (z_lsr.abs() >= 0.8) & (z_dlsr.abs() >= 0.6) & (trend < 0)

    # 5) 風控：ATR、自適應進場點與止損
    atr_n = atr(high, low, price, n=14)
    atr_norm = atr_n / price
    entry_long = price * (1 + c * atr_norm)
    entry_short = price * (1 - c * atr_norm)
    sl_long = entry_long - k_sl * atr_n
    sl_short = entry_short + k_sl * atr_n

    # 6) 部位大小：單筆風險 r 乘以 S* 強度
    S_cap = rolling_ref.quantile(0.99)
    S_scale = (S_star.abs() / S_cap.replace(0, np.nan)).clip(upper=1.0)
    base_size = (risk_pct) / (k_sl * atr_n * point_value)
    size = (base_size * S_scale).fillna(0.0)

    # 7) 追蹤停利距離
    trail_dist = k_tp * atr_n

    result = pd.DataFrame({
        'price': price,
        'S': S,
        'S_star': S_star,
        'q_hi': q_hi_series,
        'q_lo': q_lo_series,
        'trend': trend,
        'long_signal': long_cond.astype(int),
        'short_signal': short_cond.astype(int),
        'entry_long': entry_long,
        'entry_short': entry_short,
        'sl_long': sl_long,
        'sl_short': sl_short,
        'trail_dist': trail_dist,
        'size': size
    })
    return result