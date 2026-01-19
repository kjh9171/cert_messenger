# 파이썬 기본 이미지 설정
FROM python:3.10-slim

# 필요한 시스템 패키지 및 크롬 브라우저 설치
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    fonts-liberation \
    libgbm1 \
    libu2f-udev \
    libvulkan1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 구글 크롬 설치
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable

# 작업 디렉토리 설정
WORKDIR /app

# 소스 코드 복사
COPY . .

# 필요한 파이썬 라이브러리 설치
# (selenium, webdriver-manager, requests, beautifulsoup4, python-telegram-bot, schedule 등 포함)
RUN pip install --no-cache-dir requests beautifulsoup4 python-telegram-bot schedule selenium webdriver-manager

# 프로그램 실행
CMD ["python", "news_bot.py"]