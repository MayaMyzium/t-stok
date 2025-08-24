#!/usr/bin/env python3
"""
fetch_and_predict_taiwan.py
===========================

This script extends the basic example from ``fetch_and_predict.py`` by adding
support for optional global market factors and computing adaptive entry/exit
points for contracts.  It is designed to be run twice per trading day:

* **Daily prediction (around 08:30 Taiwan time)** – fetches the past year of
  daily price, volume and margin data for the Taiwan stock market and selected
  stocks (TAIEX, 2330, 0050) via the FinMind API.  A simple logistic
  regression model estimates the probability that the next day's closing price
  will rise or fall.  A predicted price range is computed using the mean and
  standard deviation of historical returns.  The output is saved to
  ``data/latest_predictions_taiwan.json``.

* **Intraday update (every 10 minutes after market open)** – optionally
  downloads minute‑level price data for the current trading day to update
  "real‑time" changes and calculates entry/exit points for long/short
  positions based on the latest closing price and the 14‑day average true
  range (ATR).  The intraday results are saved to
  ``data/realtime_taiwan.json``.  If minute data is not available, the
  intraday update can be skipped.

The model can optionally incorporate global factors such as the previous
session's returns of the S&P 500 or Nasdaq indices.  These external data can
be fetched using the ``yfinance`` package (install via pip) or replaced with
another data source.  Including global factors may help account for the
influence of U.S. market sentiment on Taiwan stocks.

**Disclaimer**: This script is for educational purposes only and does not
constitute financial advice.  Use at your own risk.

Usage::

    python fetch_and_predict_taiwan.py --mode daily   # run at 08:30
    python fetch_and_predict_taiwan.py --mode intraday # run every 10 minutes

Environment variables or command‑line options can specify your FinMind API
token and whether global factors should be included.
"""

import argparse
import json
import os
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

try:
    import yfinance as yf  # optional, used for global market data
except ImportError:
    yf = None

import requests

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# FinMind API endpoint
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

# Instruments to analyse (key → dataset + data_id)
STOCK_IDS = {
    "TaiwanIndex": {"dataset": "TaiwanStockTotalReturnIndex", "data_id": "TAIEX"},
    "2330": {"dataset": "TaiwanStockPrice", "data_id": "2330"},
    "0050": {"dataset": "TaiwanStockPrice", "data_id": "0050"},
}

# Margin purchase/short sale dataset
MARGIN_DATASET = "TaiwanStockMarginPurchaseShortSale"

# Minute‑level dataset (FinMind provides minute prices; adjust if needed)
MINUTE_DATASET = "TaiwanStockPriceMinute"

# Directory for storing data
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_dataset(dataset: str, data_id: Optional[str] = None,
                  start: Optional[str] = None, end: Optional[str] = None,
                  token: str = "") -> List[Dict]:
    """Call FinMind API and return a list of records (or empty list on error)."""
    params: Dict[str, str] = {"dataset": dataset}
    if data_id:
        params["data_id"] = data_id
    if start:
        params["start_date"] = start
    if end:
        params["end_date"] = end
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(FINMIND_URL, params=params, headers=headers, timeout=30)
        data = resp.json()
    except Exception as exc:
        print(f"Error requesting {dataset} for {data_id}: {exc}")
        return []
    if data.get("status") != 200 and data.get("status") != 'OK':
        print(f"API error ({dataset} id {data_id}): {data.get('msg', 'unknown')}")
        return []
    return data.get("data", [])


def download_daily_data(start: str, end: str, token: str = "") -> pd.DataFrame:
    """Download daily price, volume and margin data for all instruments."""
    frames = []
    for key, cfg in STOCK_IDS.items():
        # price data
        price_records = fetch_dataset(cfg["dataset"], cfg["data_id"], start, end, token)
        if not price_records:
            continue
        df_price = pd.DataFrame(price_records)
        # unify schema
        if cfg["dataset"] == "TaiwanStockTotalReturnIndex":
            df_price.rename(columns={"price": "close"}, inplace=True)
            df_price["Trading_Volume"] = np.nan
        else:
            df_price = df_price[["date", "stock_id", "Trading_Volume", "close"]]
        df_price["key"] = key
        # merge margin data if applicable
        if cfg["dataset"] != "TaiwanStockTotalReturnIndex":
            margin_records = fetch_dataset(MARGIN_DATASET, cfg["data_id"], start, end, token)
            if margin_records:
                df_margin = pd.DataFrame(margin_records)
                margin_cols = [
                    "date",
                    "stock_id",
                    "MarginPurchaseTodayBalance",
                    "MarginPurchaseYesterdayBalance",
                    "ShortSaleTodayBalance",
                    "ShortSaleYesterdayBalance",
                ]
                df_margin = df_margin[margin_cols]
                df_price = pd.merge(df_price, df_margin, on=["date", "stock_id"], how="left")
        frames.append(df_price)
    if not frames:
        raise RuntimeError("No daily data downloaded.")
    combined = pd.concat(frames, ignore_index=True)
    combined.sort_values(["key", "date"], inplace=True)
    combined.to_csv(os.path.join(DATA_DIR, "daily_data_taiwan.csv"), index=False, encoding="utf-8-sig")
    return combined


def prepare_features(df: pd.DataFrame, global_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Create features for logistic regression and optional global factors.

    Features computed per instrument:
        - return: percentage change of close price【568328348583858†screenshot】
        - volume_ratio: percentage change of Trading_Volume【568328348583858†screenshot】
        - margin_ratio: percentage change of margin purchase balances【568328348583858†screenshot】
    If ``global_df`` is provided, an additional ``us_return`` column is merged on date
    representing the prior day's return of a global index (e.g. S&P 500).
    The label ``label`` equals 1 if the next day's return is positive, otherwise 0.
    Rows lacking sufficient history are dropped.
    """
    df = df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["Trading_Volume"] = pd.to_numeric(df["Trading_Volume"], errors="coerce")
    margin_cols = [
        "MarginPurchaseTodayBalance", "MarginPurchaseYesterdayBalance",
        "ShortSaleTodayBalance", "ShortSaleYesterdayBalance"
    ]
    for col in margin_cols:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    frames = []
    for key, group in df.groupby("key"):
        g = group.sort_values("date").reset_index(drop=True)
        g["return"] = g["close"].pct_change()
        g["volume_ratio"] = g["Trading_Volume"].pct_change()
        g["margin_ratio"] = (g["MarginPurchaseTodayBalance"] - g["MarginPurchaseYesterdayBalance"]) / (
            g["MarginPurchaseYesterdayBalance"] + 1e-9)
        if global_df is not None:
            # merge on date; assume global_df has columns date and us_return
            g = pd.merge(g, global_df[["date", "us_return"]], on="date", how="left")
        # label: 1 if next day's return > 0
        g["label"] = (g["return"].shift(-1) > 0).astype(int)
        g = g.iloc[1:-1].copy()  # drop first (no return) and last (no label)
        g["key"] = key
        frames.append(g)
    features = pd.concat(frames, ignore_index=True)
    return features


def logistic_regression_train(X: np.ndarray, y: np.ndarray, lr: float = 0.1, epochs: int = 2000) -> np.ndarray:
    """Train logistic regression using gradient descent【961119570707309†screenshot】."""
    X_bias = np.hstack([np.ones((X.shape[0], 1)), X])
    beta = np.zeros(X_bias.shape[1])
    for _ in range(epochs):
        z = X_bias @ beta
        preds = 1.0 / (1.0 + np.exp(-z))
        gradient = (X_bias.T @ (preds - y)) / len(y)
        beta -= lr * gradient
    return beta


def logistic_regression_predict(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    """Predict probabilities using logistic regression coefficients【961119570707309†screenshot】."""
    X_bias = np.hstack([np.ones((X.shape[0], 1)), X])
    z = X_bias @ beta
    return 1.0 / (1.0 + np.exp(-z))


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute Average True Range (ATR) for each instrument using high/low/close.

    FinMind daily datasets do not include high/low for indexes.  As a proxy,
    this function computes ATR from close price volatility.  The 'true range'
    is approximated by the absolute difference of consecutive closes.
    """
    tr = df["close"].diff().abs()
    return tr.rolling(period).mean()


def train_and_predict(features: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Train a model per instrument and produce predictions for the latest day.

    The model uses return, volume_ratio, margin_ratio and (optional) us_return as
    features.  For each instrument, it returns the probability of rising,
    falling, and an estimated price range and adaptive entry/stop points.
    """
    results: Dict[str, Dict[str, float]] = {}
    for key, group in features.groupby("key"):
        g = group.dropna(subset=["return", "volume_ratio", "margin_ratio", "label"]).reset_index(drop=True)
        # Determine features columns
        feature_cols = ["return", "volume_ratio", "margin_ratio"]
        if "us_return" in g.columns:
            feature_cols.append("us_return")
        if len(g) < 30:
            continue
        X = g[feature_cols].values
        y = g["label"].values
        beta = logistic_regression_train(X, y)
        latest = g.iloc[-1]
        X_latest = latest[feature_cols].values.reshape(1, -1)
        prob_up = float(logistic_regression_predict(beta, X_latest)[0])
        prob_down = 1.0 - prob_up
        # Historical mean and std of returns
        mean_return = float(np.mean(g["return"].dropna()))
        std_return = float(np.std(g["return"].dropna()))
        last_close = float(latest["close"])
        pred_price = last_close * (1.0 + mean_return)
        pred_low = pred_price * (1.0 - std_return)
        pred_high = pred_price * (1.0 + std_return)
        # Adaptive entry/exit using ATR proxy
        atr_series = compute_atr(g)
        atr_value = float(atr_series.iloc[-1] if not atr_series.empty else 0)
        c = 0.3  # entry coefficient
        k_sl = 1.5  # stop loss multiplier
        k_tp = 2.0  # take profit multiplier
        entry_long = last_close * (1 + c * (atr_value / (last_close + 1e-9)))
        entry_short = last_close * (1 - c * (atr_value / (last_close + 1e-9)))
        sl_long = entry_long - k_sl * atr_value
        sl_short = entry_short + k_sl * atr_value
        tp_long = entry_long + k_tp * atr_value
        tp_short = entry_short - k_tp * atr_value
        results[key] = {
            "prob_up": round(prob_up, 4),
            "prob_down": round(prob_down, 4),
            "pred_price": round(pred_price, 2),
            "pred_low": round(pred_low, 2),
            "pred_high": round(pred_high, 2),
            "entry_long": round(entry_long, 2),
            "entry_short": round(entry_short, 2),
            "sl_long": round(sl_long, 2),
            "sl_short": round(sl_short, 2),
            "tp_long": round(tp_long, 2),
            "tp_short": round(tp_short, 2),
        }
    return results


def download_minute_data(date: str, token: str = "") -> pd.DataFrame:
    """Download minute‑level price data for all instruments for a specific date.

    FinMind's minute dataset may not be available for all instruments or may be
    subject to stricter rate limits.  This function attempts to fetch the
    current day's minute data (between 09:00–13:30) for each stock.  The
    resulting DataFrame has columns [date, time, key, close].  If the API
    returns no data, an empty DataFrame is returned.
    """
    frames = []
    for key, cfg in STOCK_IDS.items():
        records = fetch_dataset(MINUTE_DATASET, cfg["data_id"], date, date, token)
        if not records:
            continue
        df_min = pd.DataFrame(records)
        # Expect columns: date, time, close
        if "price" in df_min.columns:
            df_min.rename(columns={"price": "close"}, inplace=True)
        df_min["key"] = key
        frames.append(df_min[["date", "time", "key", "close"]])
    if not frames:
        return pd.DataFrame(columns=["date", "time", "key", "close"])
    return pd.concat(frames, ignore_index=True)


def compute_realtime_changes(min_data: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Compute percentage change relative to previous close for each instrument.

    The minute data must include at least two rows per instrument (previous
    close and current minute).  The change is (latest close / first close - 1).
    If insufficient data, change is set to 0.0.
    """
    results: Dict[str, Dict[str, float]] = {}
    for key, g in min_data.groupby("key"):
        g_sorted = g.sort_values("time")
        if len(g_sorted) < 2:
            pct_change = 0.0
            last_price = float(g_sorted["close"].iloc[-1]) if not g_sorted.empty else 0.0
        else:
            first_price = float(g_sorted["close"].iloc[0])
            last_price = float(g_sorted["close"].iloc[-1])
            pct_change = (last_price / (first_price + 1e-9)) - 1
        results[key] = {
            "last_price": round(last_price, 2),
            "pct_change": round(pct_change * 100, 2),
        }
    return results


def fetch_global_data(start: str, end: str) -> Optional[pd.DataFrame]:
    """Fetch global index data (e.g. S&P 500) using yfinance (optional)."""
    if yf is None:
        return None
    # Use SPY ETF as proxy for S&P 500
    tickers = ["SPY"]
    try:
        df = yf.download(tickers, start=start, end=end, progress=False)
        if df.empty:
            return None
        # yfinance returns MultiIndex columns; we use 'Adj Close'
        # Flatten columns if necessary
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["_".join(col).strip() for col in df.columns.values]
        # Compute daily return
        df.reset_index(inplace=True)
        df["date"] = df["Date"].dt.strftime("%Y-%m-%d")
        df["us_return"] = df["Adj Close"] / df["Adj Close"].shift(1) - 1
        return df[["date", "us_return"]]
    except Exception as exc:
        print(f"Error fetching global data: {exc}")
        return None


def run_daily(token: str, include_global: bool = False) -> None:
    """Run the daily prediction workflow."""
    today = datetime.now().date()
    start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    data = download_daily_data(start_date, end_date, token)
    global_df = None
    if include_global:
        global_df = fetch_global_data(start_date, end_date)
    features = prepare_features(data, global_df)
    preds = train_and_predict(features)
    output = {"date": end_date, "predictions": preds}
    out_path = os.path.join(DATA_DIR, "latest_predictions_taiwan.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved daily predictions to {out_path}")


def run_intraday(token: str) -> None:
    """Run the intraday update workflow."""
    # Determine today's date in local time
    today = datetime.now().date().strftime("%Y-%m-%d")
    min_data = download_minute_data(today, token)
    realtime = compute_realtime_changes(min_data)
    out_path = os.path.join(DATA_DIR, "realtime_taiwan.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "realtime": realtime}, f, ensure_ascii=False, indent=2)
    print(f"Saved intraday data to {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Taiwan stock prediction and intraday update tool")
    parser.add_argument("--mode", choices=["daily", "intraday"], required=True,
                        help="Run mode: 'daily' for morning predictions, 'intraday' for real-time updates")
    parser.add_argument("--token", type=str, default=os.environ.get("FINMIND_TOKEN", ""),
                        help="FinMind API token")
    parser.add_argument("--include-global", action="store_true",
                        help="Include global market factors using yfinance")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "daily":
        run_daily(args.token, include_global=args.include_global)
    elif args.mode == "intraday":
        run_intraday(args.token)


if __name__ == "__main__":
    main()