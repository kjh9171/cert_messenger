FROM python:3.10-slim

# 환경 변수 설정 (터미널 입력 방지 및 파이썬 출력 최적화)
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 시스템 필수 패키지 설치 및 불필요한 라이브러리 제거
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    fonts-nanum \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 구글 크롬 설치 (공식 저장소 이용)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 소스 코드 복사
COPY . .

# 파이썬 라이브러리 설치
RUN pip install --no-cache-dir requests beautifulsoup4 python-telegram-bot schedule selenium webdriver-manager

# 프로그램 실행
CMD ["python", "news_bot.py"]