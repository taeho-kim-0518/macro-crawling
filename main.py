from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from macro_crawling import MacroCrawler
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import traceback
import os
import matplotlib as mpl
import matplotlib.font_manager as fm




app = FastAPI()

@app.get("/")
def root():
    return {"message": "📈 Macro Signal API"}

@app.get("/check-today-signal")
def check_today_signal():
    try:
        crawler = MacroCrawler()
        today = pd.Timestamp.today().normalize()
        today_month = today.to_period("M")

        result = {
            "date": str(today.date()),
            "zscore_signal": [],
            "mdyoy_signal": []
        }

        df = crawler.merge_m2_margin_sp500_abs()

        # Z-Score
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

        # Margin Debt YoY
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

    except Exception as e:
        print("❌ /check-today-signal 에러:", e)
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/plot-mdyoy-graph")
def plot_mdyoy_graph():

    font_path = os.path.join("fonts", "NanumGothic.ttf")
    if os.path.exists(font_path):
        font_prop = fm.FontProperties(fname=font_path)
        mpl.rcParams['font.family'] = font_prop.get_name()
        mpl.rcParams['axes.unicode_minus'] = False
    else:
        print("❌ 폰트 파일 없음:", font_path)

    try:
        crawler = MacroCrawler()
        df = crawler.merge_m2_margin_sp500_abs()
        df = crawler.generate_mdyoy_signals(df)

        buf = BytesIO()
        crawler.plot_sp500_with_mdyoy_signals_and_graph(df, save_to=buf)
        buf.seek(0)

        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        print("❌ /plot-mdyoy-graph 에러:", e)
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/plot-zscore-graph")
def plot_zscore_graph():

    font_path = os.path.join("fonts", "NanumGothic.ttf")
    if os.path.exists(font_path):
        font_prop = fm.FontProperties(fname=font_path)
        mpl.rcParams['font.family'] = font_prop.get_name()
        mpl.rcParams['axes.unicode_minus'] = False
    else:
        print("❌ 폰트 파일 없음:", font_path)
        
    try:
        crawler = MacroCrawler()
        df = crawler.merge_m2_margin_sp500_abs()

        buf = BytesIO()
        crawler.plot_sp500_with_signals_and_graph(df, save_to=buf)
        buf.seek(0)

        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        print("❌ /plot-zscore-graph 에러:", e)
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/signal-history")
def signal_history():
    try:
        crawler = MacroCrawler()
        df = crawler.merge_m2_margin_sp500_abs()

        result = {
            "zscore_signals": [],
            "mdyoy_signals": []
        }

        zscore_df = crawler.generate_zscore_trend_signals(df)
        for _, row in zscore_df.iterrows():
            result["zscore_signals"].append({
                "signal": row["signal"],
                "original_signal_date": str(row["original_signal_date"].date()),
                "action_date": str(row["action_date"].date()),
                "expected_return_3m": round(row["return_3m"] * 100, 2)
            })

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
    except Exception as e:
        print("❌ /signal-history 에러:", e)
        traceback.print_exc()
        return {"error": str(e)}
