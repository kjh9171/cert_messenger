# 가벼운 파이썬 이미지를 사용합니다.
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템에 필요한 라이브러리 설치
RUN pip install --no-cache-dir requests beautifulsoup4 python-telegram-bot schedule google-generativeai

# 소스 코드를 컨테이너 안으로 복사
COPY news_bot.py .

# 프로그램 실행
CMD ["python", "news_bot.py"]