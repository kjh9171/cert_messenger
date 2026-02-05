
# 🚀 연합뉴스 속보 자동 발송 시스템 (Yonhap News Flash Bot)

본 프로젝트는 네이버 뉴스에서 제공하는 연합뉴스의 최신 속보를 실시간으로 수집하여 텔레그램 채널 또는 개인 봇으로 자동 전송하는 파이썬 기반 자동화 시스템입니다.

### 1. 주요 기능

* **실시간 크롤링**: 네이버 연합뉴스 속보 페이지를 모니터링하여 최신 뉴스를 수집합니다.
* **중복 방지 시스템**: 이미 발송된 기사는 데이터베이스(메모리)에서 대조하여 중복 전송을 원천 차단합니다.
* **스케줄링**: 매시간 정각마다 자동으로 작동하며, 사용자 설정에 따라 주기를 자유롭게 조절할 수 있습니다.
* **HTML 브리핑**: 텔레그램 내에서 가독성이 높은 HTML 형식으로 기사 제목과 원문 링크를 제공합니다.

### 2. 설치 및 준비 사항

본 시스템은 가상환경이 아닌 시스템 환경에서 바로 실행할 수 있도록 최적화되어 있습니다.

**필수 라이브러리 설치:**
터미널에서 아래 명령어를 입력하여 필요한 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

또는 수동으로:

```bash
pip install requests beautifulsoup4 python-telegram-bot selenium webdriver-manager schedule urllib3
```

**환경 변수 설정:**
Telegram 토큰과 채팅 ID를 환경 변수로 설정하세요.

```bash
export TELEGRAM_TOKEN='your_token_here'
export CHAT_ID='your_chat_id_here'
```

### 3. 주요 설정 정보 (Configuration)

`news_bot.py` 파일 상단의 설정 섹션에서 본인의 정보를 입력해야 합니다.

* **TELEGRAM_TOKEN**: @BotFather를 통해 발급받은 봇 API 토큰
* **CHAT_ID**: 메시지를 수신할 사용자 ID 또는 채널의 ID
* **GEMINI_API_KEY**: 이미지 생성 및 분석에 사용될 Google AI API 키

### 4. 실행 방법

**로컬 실행 (가상환경 없이):**
환경 변수를 설정한 후 실행하세요.

```bash
export TELEGRAM_TOKEN='your_token'
export CHAT_ID='your_chat_id'
python3 news_bot.py
```

**Docker 실행:**
`.env` 파일을 생성하여 환경 변수를 설정하세요.

```bash
echo "TELEGRAM_TOKEN=your_token" > .env
echo "CHAT_ID=your_chat_id" >> .env
```

그 후 Docker Compose로 실행:

```bash
docker-compose up --build -d
```

로그 확인:

```bash
docker logs news_bot_service
```

**백그라운드 실행 (로컬):**
프로그램을 종료해도 계속 실행되게 하려면 `nohup` 명령어를 사용합니다.

```bash
nohup python3 news_bot.py &
```

### 5. 파일 구조

```text
cert_messenger/
├── news_bot.py       # 메인 실행 소스코드
└── README.md         # 프로젝트 안내 파일

```

### 6. 참고 사항

* 본 봇은 네이버 뉴스의 서비스 정책을 준수하며, 과도한 요청을 방지하기 위해 스케줄러를 통한 주기적 접근 방식을 사용합니다.
* 기사 원문은 네이버 뉴스 플랫폼으로 직접 연결되어 저작권을 보호합니다.

---
