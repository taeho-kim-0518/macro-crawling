import os
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


class ISMPMIUpdater:
    def __init__(self, csv_path="ism_pmi_data.csv"):
        self.csv_path = csv_path
        try:
            self.df = pd.read_csv(self.csv_path, parse_dates=["발표일"], encoding='CP949')
            print("✅ ISM PMI CSV 불러오기 성공")
        
        except FileNotFoundError:
            print("⚠️ CSV 파일이 없어 새로 생성합니다.")
            self.df = pd.DataFrame(columns=[
                "발표일",
                "시간",
                "실제",
                "예측",
                "이전"
            ])

    # def load_existing_data(self):
    #     if os.path.exists(self.csv_path):
    #         try:
    #             df = pd.read_csv(self.csv_path)
    #             df = self._preprocess_raw_csv(df)
    #             print(f"✅ 기존 PMI CSV 로드 완료 ({len(df)} rows)")
    #             return df
    #         except Exception as e:
    #             print(f"❌ CSV 로딩 오류: {e}")
    #             return pd.DataFrame(columns=["Month/Year", "PMI"])
    #     else:
    #         print("📁 새 PMI 데이터프레임 생성")
    #         return pd.DataFrame(columns=["Month/Year", "PMI"])

    def extract_date(self, val):
        try:
            # 예: "2025년 01월 01일 (12월)"
            year_match = re.search(r"(\d{4})년", val)
            announce_month_match = re.search(r"(\d{2})월", val)  # 발표일의 달 (앞쪽)
            data_month_match = re.search(r"\((\d{1,2})월\)", val)
     
            if not (year_match and data_month_match):
                return None

            year = int(year_match.group(1))
            data_month = int(data_month_match.group(1))

            # 발표일이 다음 해이고 데이터는 12월일 수 있으므로 연도 보정 필요
            if announce_month_match:
                announce_month = int(announce_month_match.group(1))
                if data_month > announce_month:
                    year -= 1  # 데이터는 작년 12월, 발표는 1월인 경우 보정

            return pd.Timestamp(f"{year}-{data_month:02d}-01")
        except Exception as e:
            print(f"❌ 날짜 파싱 실패: {val} / {e}")
            return None

    def preprocess_raw_csv(self):
        # 발표일: "2025년 08월 01일 (7월)" → 2025-07-01
        raw_df = self.df

        df = raw_df.copy()
        df["Month/Year"] = raw_df["발표일"].apply(self.extract_date)
        df["PMI"] = pd.to_numeric(raw_df["실제"], errors="coerce")
        df = df.dropna(subset=["Month/Year", "PMI"])
        df = df[["Month/Year", "PMI"]].drop_duplicates()
        df = df.sort_values("Month/Year")
        return df
    
    def get_ism_pmi(self):
        """
        TradingEconomics 한국어 사이트에서 ISM 제조업 PMI 지표를 추출하는 함수
        """
        url = "https://ko.tradingeconomics.com/united-states/manufacturing-pmi"

        options = Options()
        # options.add_argument('--headless')  # ← 일단 꺼두세요
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        driver = webdriver.Chrome(options=options)
        driver.get(url)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table"))
            )
            soup = BeautifulSoup(driver.page_source, 'html.parser')
        except Exception as e:
            driver.quit()
            raise Exception("❌ 페이지 로딩 실패: table 요소를 찾을 수 없습니다.") from e
        finally:
            driver.quit()

        table = soup.find('table', class_='table table-hover')
        if not table:
            raise Exception("❌ 테이블을 찾을 수 없습니다.")

        rows = table.find('tbody').find_all('tr')
        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 5:
                name = columns[0].get_text(strip=True)
                if "ISM 제조업 PMI" in name:
                    value = columns[1].get_text(strip=True)
                    date = columns[4].get_text(strip=True)
                    return {
                        "지표명": name,
                        "값": value,
                        "발표일": date
                    }

        raise Exception("❌ 'ISM 제조업 PMI' 항목을 찾을 수 없습니다.")

    def parse_tradingeconomics_date(self, date_str):
        """
        'Jul 2025' → pd.Timestamp('2025-07-01')
        """
        try:
            return pd.to_datetime(date_str + "-01", format="%b %Y-%d")
        except Exception as e:
            print(f"❌ 발표일 파싱 실패: {date_str} / {e}")
            return None
        
    def update_csv(self):
        latest = self.get_ism_pmi()  # {'지표명': ..., '값': '49.00', '발표일': 'Jul 2025'}
        if not latest:
            print("❌ PMI 데이터를 가져오지 못했습니다.")
            return self.df

        # 1. 날짜 파싱
        month_year = self.parse_tradingeconomics_date(latest["발표일"])
        print("데이터 기준 연월 : ", month_year)
        if month_year is None:
            print("❌ 날짜 변환 실패")
            return self.df

        # 2. 중복 체크
        processed_df = self.preprocess_raw_csv()
        if (processed_df["Month/Year"] == month_year).any():
            print(f"📭 이미 존재하는 PMI 데이터입니다: {month_year.date()}")
            return processed_df

        # 3. 값 변환
        try:
            pmi_value = float(latest["값"])
        except:
            print("❌ PMI 값 변환 실패:", latest["값"])
            return processed_df

        # 4. 원본 df에 새 행 추가
        new_row = pd.DataFrame([{
            "발표일": month_year.strftime("%Y-%m-%d"),
            "시간": "", "실제": pmi_value, "예측": "", "이전": ""
        }])
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        print("저장된 데이터", self.df)

        # 5. 파일 저장
        self.df.to_csv(self.csv_path, index=False, encoding="cp949")
        print(f"✅ 새로운 PMI 데이터 저장 완료: {month_year.date()} / {pmi_value}")

        return processed_df

        

if __name__ == "__main__":
    cralwer = ISMPMIUpdater()

    data = cralwer.update_csv()
    print(data)

