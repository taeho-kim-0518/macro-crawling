# main.py

from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from macro_crawling import MacroCrawler  # 너가 짜둔 모듈로 경로 조정 필요
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

app = FastAPI()

@app.get("/")
def root():
    return {"message": "📈 Macro Signal API"}

@app.get("/check-today-signal")
def check_today_signal():
    crawler = MacroCrawler()
    today = pd.Timestamp.today().normalize()
    today_month = today.to_period("M")

    result = {
        "date": str(today.date()),
        "zscore_signal": [],
        "mdyoy_signal": []
    }

    # 병합된 데이터 로딩
    df = crawler.merge_m2_margin_sp500_abs()

    # --- Z-Score 전략
    zscore_df = crawler.generate_zscore_trend_signals(df)
    zscore_df["action_month"] = zscore_df["action_date"].dt.to_period("M")
    zscore_today = zscore_df[zscore_df["action_month"] == today_month]

    for _, row in zscore_today.iterrows():
        result["zscore_signal"].append({
            "signal": row["signal"],
            "original_signal_date": str(row["original_signal_date"].date()),
            "action_date": str(row["action_date"].date()),
            "expected_return_3m": round(row["return_3m"] * 100, 2)
        })

    # --- Margin Debt YoY 전략
    mdyoy_df = crawler.generate_mdyoy_signals(df)
    mdyoy_df["action_month"] = mdyoy_df["action_date"].dt.to_period("M")
    mdyoy_today = mdyoy_df[mdyoy_df["action_month"] == today_month]

    mdyoy_filtered = mdyoy_today[mdyoy_today["buy_signal"] | mdyoy_today["sell_signal"]]
    for _, row in mdyoy_filtered.iterrows():
        signal_type = "BUY" if row["buy_signal"] else "SELL"
        result["mdyoy_signal"].append({
            "signal": signal_type,
            "signal_date": str(row["signal_date"].date()),
            "action_date": str(row["action_date"].date())
        })

    return result

@app.get("/plot-mdyoy-graph")
def plot_mdyoy_graph():
    crawler = MacroCrawler()
    df = crawler.merge_m2_margin_sp500_abs()
    df = crawler.generate_mdyoy_signals(df)

    buf = BytesIO()
    crawler.plot_sp500_with_mdyoy_signals_and_graph(df, save_to=buf)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

@app.get("/plot-zscore-graph")
def plot_zscore_graph():
    crawler = MacroCrawler()
    df = crawler.merge_m2_margin_sp500_abs()

    buf = BytesIO()
    crawler.plot_sp500_with_signals_and_graph(df, save_to=buf)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

@app.get("/signal-history")
def signal_history():
    crawler = MacroCrawler()
    df = crawler.merge_m2_margin_sp500_abs()

    result = {
        "zscore_signals": [],
        "mdyoy_signals": []
    }

    # Z-Score 전략
    zscore_df = crawler.generate_zscore_trend_signals(df)
    for _, row in zscore_df.iterrows():
        result["zscore_signals"].append({
            "signal": row["signal"],
            "original_signal_date": str(row["original_signal_date"].date()),
            "action_date": str(row["action_date"].date()),
            "expected_return_3m": round(row["return_3m"] * 100, 2)
        })

    # Margin Debt YoY 전략
    mdyoy_df = crawler.generate_mdyoy_signals(df)
    filtered_df = mdyoy_df[mdyoy_df["buy_signal"] | mdyoy_df["sell_signal"]]
    for _, row in filtered_df.iterrows():
        signal_type = "BUY" if row["buy_signal"] else "SELL"
        result["mdyoy_signals"].append({
            "signal": signal_type,
            "signal_date": str(row["signal_date"].date()),
            "action_date": str(row["action_date"].date())
        })

    return result