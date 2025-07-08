# Dockerfile
FROM python:3.10-slim

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    chromium-driver \
    chromium \
    wget \
    curl \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxss1 \
    libappindicator1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libu2f-udev \
    fonts-liberation \
    xdg-utils

# 작업 디렉토리 생성 및 코드 복사
WORKDIR /app
COPY . /app

# Python 패키지 설치
RUN pip install --upgrade pip && pip install -r requirements.txt

# 환경 변수 설정 (Selenium용)
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 실행 명령어
CMD ["streamlit", "run", "market_dashboard.py", "--server.port=8000", "--server.enableCORS=false"]
