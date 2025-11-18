import os
import pandas as pd
import requests
from bs4 import BeautifulSoup

def smart_parse_month_year(val):
    try:
        parts = val.strip().split('-')
        if len(parts) != 2:
            return None

        # 월-연도 또는 연도-월 처리
        if parts[0].isalpha():  # 예: 'May-25'
            month_part = parts[0]
            year_part = parts[1]
        else:  # 예: '25-May'
            year_part = parts[0]
            month_part = parts[1]

        year_int = int(year_part)
        full_year = 2000 + year_int if year_int < 50 else 1900 + year_int

        return pd.to_datetime(f"{full_year}-{month_part}-01", format="%Y-%b-%d")
    except:
        return None

def fix_md_csv_format(file_path="md_df.csv", backup=True):
    if not os.path.exists(file_path):
        print(f"❌ 파일이 존재하지 않습니다: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        # ✅ 컬럼명 보정: Year-Month → Month/Year
        if "Month/Year" not in df.columns:
            if "Year-Month" in df.columns:
                df.rename(columns={"Year-Month": "Month/Year"}, inplace=True)
                print("🔄 'Year-Month' → 'Month/Year' 컬럼명 자동 변경")
            else:
                print("❌ 'Month/Year' 또는 'Year-Month' 컬럼이 없습니다.")
                return

        print("📂 원본 날짜 샘플:")
        print(df["Month/Year"].head())

        # 날짜 수동 파싱
        df["Month/Year"] = df["Month/Year"].apply(smart_parse_month_year)
        df = df.dropna(subset=["Month/Year"])

        # 저장 전 ISO 형식으로 변환
        df["Month/Year"] = df["Month/Year"].dt.strftime("%Y-%m-%d")

        # if backup:
        #     backup_path = file_path.replace(".csv", "_backup.csv")
        #     os.rename(file_path, backup_path)
        #     print(f"💾 백업 저장: {backup_path}")

        df.to_csv(file_path, index=False)
        print(f"✅ CSV 날짜 포맷 정리 완료: {file_path}")

    except Exception as e:
        print("❌ 처리 오류:", e)

class MarginDebtUpdater :
    def __init__(self, csv_path="md_df.csv"):
        self.csv_path = csv_path
        try:
            self.df = pd.read_csv(self.csv_path, parse_dates=["Month/Year"])
            print("✅ 마진 부채 CSV 불러오기 성공")
        
        except FileNotFoundError:
            print("⚠️ CSV 파일이 없어 새로 생성합니다.")
            self.df = pd.DataFrame(columns=[
                "Month/Year",
                "Debit Balances in Customers' Securities Margin Accounts",
                "Free Credit Balances in Customers' Cash Accounts",
                "Free Credit Balances in Customers' Securities Margin Accounts"
            ])

    def get_margin_debt_data(self):
        url = "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            print("❌ 마진 부채 페이지 요청 실패:", e)
            print("📦 응답 내용:", response.text)
            return pd.DataFrame()

        table = soup.select_one("table")
        rows = table.find_all("tr")

        data = []
        headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]

        # for row in rows[1:]:
        #     cols = [td.get_text(strip=True).replace(",", "") for td in row.find_all("td")]
        #     if len(cols) == len(headers):
        #         data.append(cols)

        # df = pd.DataFrame(data, columns=headers)
        # df["Month/Year"] = pd.to_datetime(df["Month/Year"], format="%b-%y")

        # for col in df.columns[1:]:
        #     df[col] = pd.to_numeric(df[col], errors="coerce")

        for row in rows[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cols) == len(headers):
                    data.append(cols)

        df = pd.DataFrame(data, columns=headers)

        try:
            df["Month/Year"] = pd.to_datetime(df["Month/Year"], format="%b-%y")
        except:
            df["Month/Year"] = df["Month/Year"].apply(smart_parse_month_year)

        # 모든 숫자형 컬럼 안전하게 변환
        for col in df.columns[1:]:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df


    def update_csv(self):

        new_df = self.get_margin_debt_data()
        # 날짜 타입 정리
        new_df["Month/Year"] = pd.to_datetime(new_df["Month/Year"], errors="coerce")
        self.df["Month/Year"] = pd.to_datetime(self.df["Month/Year"], errors="coerce")

        # 기존에 없는 날짜만 필터링
        new_rows = new_df[~new_df["Month/Year"].isin(self.df["Month/Year"])]

        if not new_rows.empty:
            print(f"🆕 {len(new_rows)}개의 새 행이 추가됩니다.")

            updated = pd.concat([self.df, new_rows], ignore_index=True).dropna(subset=["Month/Year"])
            updated = updated.sort_values("Month/Year")

            # ✅ 저장 전 날짜를 문자열로 포맷 (일관성 유지)
            updated["Month/Year"] = updated["Month/Year"].dt.strftime("%Y-%m-%d")
            updated.to_csv(self.csv_path, index=False)

            # ✅ self.df도 업데이트 후 datetime 재변환
            updated["Month/Year"] = pd.to_datetime(updated["Month/Year"])
            self.df = updated
        else:
            print("📭 새로운 데이터 없음. CSV 업데이트 건너뜀.")

        return self.df

# 문자열 날짜 바꿀 때 사용
if __name__ == "__main__":
#     fix_md_csv_format("md_df.csv")
    update = MarginDebtUpdater()

    result = update.update_csv()
