#!/usr/bin/env python3
"""
fetch_and_predict.py
====================

This script downloads daily price and margin data for Taiwan's stock market and
selected stocks via the FinMind data API. It then builds a simple logistic
regression model to estimate the probability that the next trading day's
closing price will rise (1) or fall (0). The trained model is used to
generate predictions for the latest available date, including an estimated
price range based on historical volatility. Results are written to a JSON file
(`data/latest_predictions.json`) and the raw daily data is stored as a CSV
(`data/daily_data.csv`).

The code is intentionally self‑contained and does not depend on external
machine learning libraries. All numerical computations are handled with
NumPy.  If you provide your FinMind API token, the script can download up
to 600 requests/hour; without a token the limit is lower.

Usage::

    python fetch_and_predict.py

Configuration:
    TOKEN:     your FinMind API token, set below or via environment
    START_DATE: start date for historical data (YYYY-MM-DD)
    END_DATE:   end date for historical data (YYYY-MM-DD)

Output files:
    data/daily_data.csv         – combined dataset for all instruments
    data/latest_predictions.json – model predictions for the most recent day

Disclaimer:
    The model implemented here is extremely simplified and intended purely
    for educational purposes.  It does not constitute financial advice. Use
    at your own risk.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd
import requests

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Set your FinMind API token here.  You can also set the FINMIND_TOKEN
# environment variable instead of hard‑coding it.
TOKEN: str = os.environ.get("FINMIND_TOKEN", "")  # e.g. "your_token_here"

# Date range for historical data.  Use the last year by default.
today = datetime.now().date()
START_DATE: str = (today - timedelta(days=365)).strftime("%Y-%m-%d")
END_DATE: str = (today - timedelta(days=1)).strftime("%Y-%m-%d")

# Stock identifiers for analysis
STOCK_IDS = {
    "TaiwanIndex": {
        "dataset": "TaiwanStockTotalReturnIndex",
        "data_id": "TAIEX",  # 加權指數
    },
    "2330": {
        "dataset": "TaiwanStockPrice",
        "data_id": "2330",  # 台積電
    },
    "0050": {
        "dataset": "TaiwanStockPrice",
        "data_id": "0050",  # 元大台灣50
    },
}

# Additional dataset for margin purchase and short sale
MARGIN_DATASET = "TaiwanStockMarginPurchaseShortSale"

# Directory where data and results will be stored
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# URL for FinMind API
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

def fetch_dataset(dataset: str, data_id: str = None, start: str = None,
                  end: str = None, token: str = "") -> List[Dict]:
    """Call the FinMind API and return a list of records.

    Args:
        dataset: The dataset name, e.g. 'TaiwanStockPrice'.
        data_id: Optional identifier (stock code or index id).
        start:   ISO date (YYYY-MM-DD) for the start of the period.
        end:     ISO date (YYYY-MM-DD) for the end of the period.
        token:   API token for elevated rate limits.

    Returns:
        A list of dictionaries representing the returned data.  If the
        request fails or the API responds with an error, an empty list is
        returned and a warning is printed to stderr.
    """
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
    except Exception as exc:
        print(f"Error requesting {dataset} for {data_id}: {exc}")
        return []
    try:
        data = resp.json()
    except Exception:
        print(f"Non‑JSON response for dataset {dataset} id {data_id}: {resp.text[:100]}")
        return []
    if data.get("status") != 200 and data.get("status") != 'OK':
        # API may return a status code or simple OK string
        # Print message and return empty list
        msg = data.get("msg", "Unknown error")
        print(f"API error ({dataset} id {data_id}): {msg}")
        return []
    return data.get("data", [])


def download_data(token: str = "") -> pd.DataFrame:
    """Download historical price and margin data for all instruments.

    Returns a DataFrame with combined data for analysis.  Each instrument's
    daily record will include closing price, trading volume, and margin
    purchase / short sale balances.  Records are aligned by date.
    """
    all_frames = []
    for key, cfg in STOCK_IDS.items():
        # Fetch price data
        price_records = fetch_dataset(cfg["dataset"], cfg["data_id"], START_DATE, END_DATE, token)
        if not price_records:
            continue
        df_price = pd.DataFrame(price_records)
        # Standardize column names
        if cfg["dataset"] == "TaiwanStockTotalReturnIndex":
            df_price.rename(columns={"price": "close"}, inplace=True)
            df_price["Trading_Volume"] = np.nan  # index does not have volume
        else:
            # Rename to unify schema
            df_price = df_price[["date", "stock_id", "Trading_Volume", "close"]]
        df_price["key"] = key
        # Fetch margin data for stocks (not applicable to index)
        if cfg["dataset"] != "TaiwanStockTotalReturnIndex":
            margin_records = fetch_dataset(MARGIN_DATASET, cfg["data_id"], START_DATE, END_DATE, token)
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
                # Merge margin data on date and stock_id
                df_price = pd.merge(df_price, df_margin, on=["date", "stock_id"], how="left")
        all_frames.append(df_price)
    if not all_frames:
        raise RuntimeError("No data downloaded. Please check your API token and network connectivity.")
    combined = pd.concat(all_frames, ignore_index=True)
    combined.sort_values(["key", "date"], inplace=True)
    # Store combined data
    combined.to_csv(os.path.join(DATA_DIR, "daily_data.csv"), index=False, encoding="utf-8-sig")
    return combined


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create additional features for modeling.

    For each instrument, compute:
      - daily return (pct change of close)
      - volume change ratio (pct change of Trading_Volume)
      - margin change ratio (margin purchase today vs yesterday)

    The resulting DataFrame contains the original data plus new feature columns
    and a label indicating whether the next day's close is higher (1) or not (0).
    Rows without sufficient history for computing the label are dropped.
    """
    df = df.copy()
    # Ensure numeric types
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["Trading_Volume"] = pd.to_numeric(df["Trading_Volume"], errors="coerce")
    # Margin fields may be NaN for index; fill with 0
    margin_cols = [
        "MarginPurchaseTodayBalance",
        "MarginPurchaseYesterdayBalance",
        "ShortSaleTodayBalance",
        "ShortSaleYesterdayBalance",
    ]
    for col in margin_cols:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    feature_frames = []
    for key, group in df.groupby("key"):
        g = group.sort_values("date").reset_index(drop=True)
        # Compute return
        g["return"] = g["close"].pct_change()
        # Volume change
        g["volume_ratio"] = g["Trading_Volume"].pct_change()
        # Margin change
        g["margin_ratio"] = (g["MarginPurchaseTodayBalance"] - g["MarginPurchaseYesterdayBalance"]) / (
            g["MarginPurchaseYesterdayBalance"] + 1e-9
        )
        # Label: next day up (1) or down (0).  We shift return by -1 to align with current day features
        g["label"] = (g["return"].shift(-1) > 0).astype(int)
        # Drop first row (no return) and last row (no label)
        g = g.iloc[1:-1].copy()
        feature_frames.append(g)
    features = pd.concat(feature_frames, ignore_index=True)
    return features


def logistic_regression_train(X: np.ndarray, y: np.ndarray, lr: float = 0.1, epochs: int = 2000) -> np.ndarray:
    """Train a simple logistic regression model using gradient descent.

    Args:
        X: Feature matrix of shape (n_samples, n_features).
        y: Binary labels (0/1) of shape (n_samples,).
        lr: Learning rate.
        epochs: Number of iterations.

    Returns:
        beta: Weight vector including bias term, shape (n_features + 1,).
    """
    # Add bias term
    X_bias = np.hstack([np.ones((X.shape[0], 1)), X])
    beta = np.zeros(X_bias.shape[1])
    for _ in range(epochs):
        z = X_bias @ beta
        predictions = 1.0 / (1.0 + np.exp(-z))
        gradient = (X_bias.T @ (predictions - y)) / len(y)
        beta -= lr * gradient
    return beta


def logistic_regression_predict(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    """Predict probabilities using trained logistic regression coefficients.

    Args:
        beta: Weight vector including bias term.
        X: Feature matrix, shape (n_samples, n_features).

    Returns:
        Probabilities of the positive class.
    """
    X_bias = np.hstack([np.ones((X.shape[0], 1)), X])
    z = X_bias @ beta
    return 1.0 / (1.0 + np.exp(-z))


def train_and_predict(features: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Train a model per instrument and generate the latest predictions.

    Args:
        features: DataFrame returned by `prepare_features`.

    Returns:
        Dictionary with prediction results for each instrument.  Each entry
        contains the predicted probability of rising (`prob_up`), probability of
        falling (`prob_down`), predicted price (`pred_price`), and lower/upper
        bounds (`pred_low`, `pred_high`).
    """
    results: Dict[str, Dict[str, float]] = {}
    for key, group in features.groupby("key"):
        g = group.reset_index(drop=True)
        # Drop rows with NaNs in feature columns
        g = g.dropna(subset=["return", "volume_ratio", "margin_ratio", "label"])
        if len(g) < 30:
            # Not enough data to train a model; skip
            continue
        X = g[["return", "volume_ratio", "margin_ratio"]].values
        y = g["label"].values
        beta = logistic_regression_train(X, y)
        # Latest row features (second last original row) for prediction
        latest = g.iloc[-1]
        X_latest = latest[["return", "volume_ratio", "margin_ratio"]].values.reshape(1, -1)
        prob_up = float(logistic_regression_predict(beta, X_latest)[0])
        prob_down = 1.0 - prob_up
        # Estimate price using historical mean return and std over the training period
        mean_return = float(np.mean(g["return"].dropna()))
        std_return = float(np.std(g["return"].dropna()))
        last_close = float(latest["close"])
        # Predicted price = last close * (1 + mean_return)
        pred_price = last_close * (1.0 + mean_return)
        pred_low = pred_price * (1.0 - std_return)
        pred_high = pred_price * (1.0 + std_return)
        results[key] = {
            "prob_up": round(prob_up, 4),
            "prob_down": round(prob_down, 4),
            "pred_price": round(pred_price, 2),
            "pred_low": round(pred_low, 2),
            "pred_high": round(pred_high, 2),
        }
    return results


def main() -> None:
    # Download data
    print(f"Downloading data from {START_DATE} to {END_DATE}…")
    data = download_data(TOKEN)
    print(f"Downloaded {len(data)} records for {len(STOCK_IDS)} instruments.")
    # Prepare features
    features = prepare_features(data)
    print(f"Prepared feature set with {len(features)} rows.")
    # Train and predict
    predictions = train_and_predict(features)
    if not predictions:
        raise RuntimeError("No predictions generated; insufficient data.")
    # Compose output JSON
    output = {
        "date": END_DATE,
        "predictions": predictions,
    }
    output_path = os.path.join(DATA_DIR, "latest_predictions.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved predictions to {output_path}.")


if __name__ == "__main__":
    main()