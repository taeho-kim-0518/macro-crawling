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

font_path = os.path.join("fonts", "NanumGothic.ttf")
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    font_prop = fm.FontProperties(fname=font_path)
    mpl.rcParams["font.family"] = font_prop.get_name()
    mpl.rcParams["axes.unicode_minus"] = False
    print(f"✅ 폰트 등록 완료: {font_prop.get_name()}")
else:
    print("❌ NanumGothic.ttf 폰트 파일이 없습니다.")


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

@app.get("/rate-correlations")
def rate_correlations(show_plot: bool = False):
    """
    S&P500과 실질 10Y 금리 및 금리스프레드 간 상관관계 분석.
    show_plot=True이면 히트맵 이미지를 스트리밍으로 반환.
    """
    try:
        crawler = MacroCrawler()
        result = crawler.analyze_rate_correlations(show_plot=False)

        # show_plot 파라미터가 True이면 히트맵을 그려 StreamingResponse로 반환
        if show_plot:
            sp500   = crawler.get_sp500()
            df_10y  = crawler.get_10years_treasury_yeild()
            df_2y   = crawler.get_2years_treasury_yeild()
            cpi_yoy = crawler.get_cpi_yoy()
            fed     = crawler.get_fed_funds_rate()

            # 월 단위 날짜 통일
            for df in [sp500, df_10y, df_2y, cpi_yoy, fed]:
                df['date'] = pd.to_datetime(df['date']).dt.to_period('M').dt.to_timestamp()

            # 병합 및 상관행렬 계산(위에서 수정한 컬럼 생성 포함)
            df = sp500.merge(df_10y[['date','value']], on='date').rename(columns={'value':'10y'})
            df = df.merge(df_2y[['date','value']], on='date').rename(columns={'value':'2y'})
            df = df.merge(cpi_yoy[['date','CPI YOY(%)']], on='date').rename(columns={'CPI YOY(%)':'cpi_yoy'})
            df = df.merge(fed[['date','fed_funds_rate']], on='date')
            df['real_10y'] = df['10y'] - df['cpi_yoy']
            df['spread']   = df['10y'] - df['2y']
            df['ffr_vs_2y']= df['fed_funds_rate'] - df['2y']

            corr = df[['sp500_close','real_10y','spread']].corr()

            # 히트맵 이미지 생성
            import matplotlib.pyplot as plt
            import seaborn as sns
            plt.figure(figsize=(8,6))
            sns.heatmap(corr, annot=True, fmt=".2f", cmap='coolwarm', square=True)
            plt.title("S&P500과 금리 관련 지표 간 상관관계")
            buf = BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)
            return StreamingResponse(buf, media_type="image/png")

        # show_plot=False이면 JSON 반환
        return result

    except Exception as e:
        print("❌ /rate-correlations 에러:", e)
        traceback.print_exc()
        return {"error": str(e)}
    

@app.get("/plot-sell-signals")
def plot_sell_signals():
    try:
        crawler = MacroCrawler()
        df = crawler.generate_rate_cut_signals()
        buf = BytesIO()
        # plot_sp500_with_sell_signals는 plt.show() 대신 savefig를 지원하므로 save_to 인자로 BytesIO 전달
        crawler.plot_sp500_with_sell_signals()  # 필요하다면 수정하여 save_to 매개변수 추가
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return {"error": str(e)}
    

@app.get("/plot-buy-signals")
def plot_buy_signals():
    try:
        crawler = MacroCrawler()
        df = crawler.generate_buy_signals_from_hike()
        buf = BytesIO()
        crawler.plot_buy_signals_from_hike()  # 마찬가지로 save_to 매개변수를 추가하는 편이 좋습니다.
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return {"error": str(e)}