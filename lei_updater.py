import os
import pandas as pd
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup



class LEIUpdater:
    def __init__(self, csv_path="lei_data.csv"):
        self.csv_path = csv_path
        try:
            self.df = pd.read_csv(self.csv_path, parse_dates=["date"], encoding='CP949')
            # self.df.columns = self.df.columns.str.strip()
            # self.df.columns = self.df.columns.str.replace('\ufeff', '', regex=False)
            print("✅ LEI CSV 불러오기 성공")
        
        except FileNotFoundError:
            print("⚠️ CSV 파일이 없어 새로 생성합니다.")
            self.df = pd.DataFrame(columns=[
                "Month/Year",
                "PMI"
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
        # df["Month/Year"] = raw_df["발표일"].apply(self.extract_date)
        # df["PMI"] = pd.to_numeric(raw_df["실제"], errors="coerce")
        df = df.dropna(subset=["date", "value"])
        df = df[["date", "value"]].drop_duplicates()
        df = df.sort_values("date")
        return df
    
    def get_us_leading_index_actual(self):
        """
        TradingEconomics 웹 페이지에서 미국 선행 지수의 실제값을 가져옵니다.

        Args:
            url (str): 데이터를 가져올 TradingEconomics 페이지의 URL.

        Returns:
            str: 실제값 (예: '98.80') 또는 찾을 수 없는 경우 None.
        """

        url = "https://ko.tradingeconomics.com/united-states/leading-economic-index"
    
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        extracted_data = []

        try:
            # 웹 페이지에 GET 요청 보내기
            print(f"URL에 접속 중: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status() # HTTP 오류가 발생하면 예외 발생

            # BeautifulSoup으로 HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')

            # 'ctl00_ContentPlaceHolder1_ctl00_ctl00_PanelPeers' ID를 가진 div를 찾습니다.
            panel_peers_div = soup.find('div', id='ctl00_ContentPlaceHolder1_ctl00_ctl00_PanelPeers')
            
            if panel_peers_div:
                # 해당 div 안에서 'table-responsive' 클래스를 가진 div를 찾고 그 안의 'table table-hover' 테이블을 찾습니다.
                table_responsive_div = panel_peers_div.find('div', class_='table-responsive')
                if table_responsive_div:
                    data_table = table_responsive_div.find('table', class_='table table-hover')
                    
                    if data_table:
                        # 테이블 헤더 추출
                        header_row = data_table.find('thead').find('tr')
                        if header_row:
                            headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
                            # 첫 번째 빈 헤더 제거
                            if headers and headers[0] == '':
                                headers = headers[1:]
                            print(f"추출된 헤더: {headers}") # 디버깅용

                            # '마지막'과 '참고' 열의 인덱스 찾기
                            try:
                                last_index = headers.index("마지막")
                                ref_date_index = headers.index("참고")
                            except ValueError as e:
                                print(f"ERROR: 필요한 헤더('마지막' 또는 '참고')를 찾을 수 없습니다: {e}")
                                return []

                            # 데이터 행 순회: tbody 유무와 상관없이 테이블 내의 모든 <tr>을 찾고, 헤더 다음 행부터 데이터로 처리
                            all_table_rows = data_table.find_all('tr')
                            
                            # 헤더 행 다음부터 실제 데이터 행으로 간주
                            # 헤더가 <thead> 안에 있고, 데이터는 <tbody> 안에 명시될 수도 있지만,
                            # <tbody>가 없는 경우 <tr>이 <table> 바로 아래에 올 수 있음.
                            # 따라서 thead 안의 tr을 제외한 나머지 tr을 가져옵니다.
                            data_rows = [row for row in all_table_rows if row.find_parent('thead') is None]

                            if data_rows:
                                for row in data_rows:
                                    # 첫 번째 td는 지표 이름이므로 따로 처리
                                    indicator_name_tag = row.find('td', style="padding-left: 10px; text-align: left;")
                                    indicator_name = indicator_name_tag.get_text(strip=True) if indicator_name_tag else "N/A"

                                    # 지표 이름 셀을 제외한 나머지 셀에서 값을 추출합니다.
                                    data_cells_excluding_indicator_name = row.find_all('td')[1:] 
                                    processed_data_cells = [cell.get_text(strip=True) for cell in data_cells_excluding_indicator_name]

                                    last_value = None
                                    ref_date = None

                                    # 추출된 헤더의 인덱스에 따라 값을 가져옵니다.
                                    if last_index < len(processed_data_cells):
                                        last_value = processed_data_cells[last_index]
                                    if ref_date_index < len(processed_data_cells):
                                        ref_date = processed_data_cells[ref_date_index]
                                    
                                    extracted_data.append({
                                        "indicator": indicator_name,
                                        "value": last_value,
                                        "date": ref_date
                                    })
                            else:
                                print("ERROR: 테이블에서 데이터 행(<tr>)을 찾을 수 없습니다.")
                        else:
                            print("ERROR: 테이블 헤더 행(<thead><tr>)을 찾을 수 없습니다.")
                    else:
                        print("ERROR: 'table table-hover' 클래스를 가진 테이블을 찾을 수 없습니다.")
                else:
                    print("ERROR: 'table-responsive' div를 찾을 수 없습니다.")
            else:
                print("ERROR: 'ctl00_ContentPlaceHolder1_ctl00_ctl00_PanelPeers' ID를 가진 div를 찾을 수 없습니다.")

        except requests.exceptions.RequestException as e:
            print(f"웹 페이지에 접속하는 중 오류 발생: {e}")
        except Exception as e:
            print(f"데이터를 파싱하는 중 오류 발생: {e}")
        
        return extracted_data[0]


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
        latest = self.get_us_leading_index_actual()  # {'지표명': ..., '값': '49.00', '발표일': 'Jul 2025'}
        if not latest:
            print("❌ LEI 데이터를 가져오지 못했습니다.")
            return self.df

        # 1. 날짜 파싱
        month_year = self.parse_tradingeconomics_date(latest["date"])
        print("데이터 기준 연월 : ", month_year)
        if month_year is None:
            print("❌ 날짜 변환 실패")
            return self.df

        # 2. 중복 체크
        processed_df = self.df
        
        if (processed_df["date"] == month_year).any():
            print(f"📭 이미 존재하는 LEI 데이터입니다: {month_year.date()}")
            return processed_df

        # 3. 값 변환
        try:
            lei_value = float(latest["value"])
        except:
            print("❌ LEI 값 변환 실패:", latest["value"])
            return processed_df

        # 4. 원본 df에 새 행 추가
        new_row = pd.DataFrame([{
            "date": month_year.strftime("%Y-%m-%d"),
            "value" : lei_value
        }])
        self.df = pd.concat([self.df, new_row], ignore_index=True)


        # 5. 저장
        try:
            self.df.to_csv(self.csv_path, index=False, encoding="CP949")
            print(f"✅ 새로운 PMI 데이터 저장 완료: {month_year.date()} / {lei_value}")
        except Exception as e:
            print("❌ CSV 저장 중 오류 발생:", e)

        return self.df 

        

if __name__ == "__main__":
    cralwer = LEIUpdater()

    data = cralwer.update_csv()
    print(data)

