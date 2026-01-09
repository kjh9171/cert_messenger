# Cert Messenger — Overview & Operations

이 문서는 프로젝트의 아키텍처, 핵심 동작 원리(일회성 메시지 vs 로컬 대시보드), 서비스 시작 및 운영(관리) 방법을 정리합니다.

---

## 1. 전체 아키텍처

```mermaid
flowchart LR
  subgraph Client
    C1[Electron 데스크탑 클라이언트<br/>로컬 대시보드 (data/db.json)]
  end

  subgraph Network
    S[중앙 서버<br/>Express + Socket.IO + lowdb]
  end

  C1 -- Socket.IO/HTTP --> S

  note right of S
    - 채널/메시지(서버 측 저장은 선택적)\n    - ephemeral 메시지 관리\n    - 브로드캐스트 API
  end

  style Client fill:#f3f9ff,stroke:#333
  style Network fill:#fff3f3,stroke:#333
```

설명
- 클라이언트: Electron 기반 로컬 앱. 개인 `대시보드(메모/일정)`은 로컬에 저장됩니다 (`/data/db.json`).
- 중앙 서버: 다수의 클라이언트가 접속하여 채널을 공유할 수 있는 서버입니다. 메시지는 기본적으로 비영구(ephemeral)이며, 클라이언트가 `Persistent` 표시한 경우에만 서버에 영구 저장됩니다.

---

## 2. 핵심 동작 원리

- 장면: A가 채널 생성 → B가 동일 채널에 접속 → 실시간 메시지 교환
- 메시지 영속성 규칙:
  - 기본: 비영구(ephemeral). 클라이언트가 `Persistent` 체크박스를 켜야 서버에 영구 저장됩니다.
  - `leaveChannel` 이벤트: 사용자가 채널을 떠나면 그 사용자가 작성한 비영구 메시지는 삭제됩니다.
  - 채널에 남은 멤버가 없으면 서버는 해당 채널의 모든 비영구 메시지를 정리(삭제)합니다.
  - 서버(관리자)는 `POST /api/channels/:id/broadcast`로 영구 공지(persistent)를 보낼 수 있습니다.

- 로컬 대시보드(클라이언트): 개인 메모/일정은 클라이언트 측에 저장되고 서버와는 분리됩니다. 데이터는 `data/db.json`에 보관됩니다.

---

## 3. 파일 위치 요약

- 데스크탑 클라이언트 루트
  - `main.js` (Electron main)
  - `renderer/` (UI 파일)
  - `data/db.json` (로컬 대시보드 및 클라이언트 상태)
- 중앙 서버
  - `server/index.js`
  - `server/db.json` (서버 저장 데이터)

---

## 4. 빠른 시작 — 개발용 로컬 실행

1) 중앙 서버 실행 (로컬 또는 원격)

```bash
cd server
npm install
# 개발용: 직접 실행
node index.js

# (선택) 백그라운드 관리: PM2 예시
# npm i -g pm2
# pm2 start index.js --name cert-server
# pm2 logs cert-server
```

기본 포트: `4000` (http://localhost:4000)

2) 데스크탑 클라이언트 실행

```bash
# 프로젝트 루트
npm install
npm start
```

클라이언트에서 `Server URL`에 중앙 서버 주소(예: `http://localhost:4000`) 입력 후 `Connect` 클릭.

3) 간단 테스트

- 채널 생성 → 다른 클라이언트(또는 동일 머신에서 다른 인스턴스)가 같은 채널에 Join → 메시지 작성
- 메시지 `Persistent` 체크를 해제하면 퇴장 시 삭제되는 일회성 메시지로 동작

---

## 5. 운영(관리) 가이드

- 서버를 서비스로 상시 운영하려면 다음 중 하나 권장:
  - PM2: 프로세스 관리(재시작, 로그)
  - systemd 서비스 파일: 부팅 시 자동 시작
  - Docker: 컨테이너로 패키징하여 배포

예: PM2로 배포

```bash
cd server
pm2 start index.js --name cert-server
pm2 save            # 재부팅 후 복원
pm2 logs cert-server
```

Docker(간단) 예시

```bash
# server 디렉토리에서
docker run -d -p 4000:4000 --name cert-server -v $PWD/db.json:/app/db.json node:18 node index.js
docker logs -f cert-server
```

로그 확인
- 서버: `pm2 logs cert-server` 또는 `docker logs -f cert-server` 또는 직접 실행한 터미널
- 클라이언트: Electron 창의 개발자 도구(콘솔) 또는 실행 터미널에 출력

데이터 백업
- 클라이언트 로컬 대시보드: `data/db.json`을 정기적으로 백업(복사)
- 서버: `server/db.json` 백업

보안 권장사항 (운영 전 필수)
- HTTPS(리버스 프록시 nginx + Let's Encrypt)
- 인증 (JWT/OAuth) 및 권한 관리
- 요청 속도 제한(rate limiting) 및 로깅

---

## 6. 변경/수정 이력 (요약)

- 메시지 기본 동작: 비영구(ephemeral) 전환(클라이언트가 `persistent` 지정 시만 영구 저장)
- 채널 멤버십 관리: `joinChannel` / `leaveChannel` 이벤트로 멤버 목록 갱신 및 비영구 메시지 정리
- 서버 브로드캐스트 API 추가: `POST /api/channels/:id/broadcast`
- 클라이언트: 로컬 대시보드(로컬 저장) 및 Server URL 입력 기능 추가

---

문제가 발생하면 실행 로그와 함께 알려주세요. 원하시면 `systemd` 서비스 예시 파일이나 `Dockerfile`/`docker-compose.yml` 샘플을 추가로 만들어 드리겠습니다.
# Cert Messenger — Quick Guide

간단 사용 흐름과 흐름도를 정리한 문서입니다. 로컬에서 빠르게 프로토타입을 띄우고, 인증·채널·메시지(메모) 흐름을 이해하는 데 참고하세요.

## 빠른 시작

프로젝트 루트에서:

```bash
docker-compose up --build
```

- 프론트엔드: http://localhost:8080
- 백엔드 API: http://localhost:3100

## 간단 사용 흐름

1. 사용자 등록 (전화/이메일 입력)
   - `POST /api/register` { contact, type }
   - 서버(데모)는 확인 코드를 Redis에 저장하고 응답으로 반환합니다.
2. 코드 검증 및 JWT 발급
   - `POST /api/verify` { contact, type, code } → JWT 반환
3. 채널 생성
   - `POST /api/channels` (헤더에 `Authorization: Bearer <JWT>` 선택 가능)
   - 응답: `{ channelId, channelLink }` (링크를 공유하여 누구나 접근 가능)
4. 채널 접속 (웹 클라이언트)
   - 웹에서 채널 ID/링크 입력 → Socket.IO를 통해 `joinChannel` 이벤트 전송
5. 메모/할일 작성
   - 클라이언트에서 `saveNote` 이벤트 전송 (TTL 옵션 가능)
   - 서버는 DB에 저장 후 채널의 모든 클라이언트에 `noteAdded` 브로드캐스트
6. E2E 공개키 등록 (선택)
   - 클라이언트에서 키페어 생성 후 `POST /api/keys`로 공개키 업로드
   - 서버는 사용자의 `public_key`를 DB에 저장

## 흐름도 (Mermaid)

다음 Mermaid 도표는 위의 주요 흐름을 요약합니다. GitHub에서 렌더링되는 Mermaid 블록입니다.

```mermaid
flowchart TD
  A[사용자 입력: 연락처] --> B[POST /api/register]
  B --> C[Redis에 코드 저장]
  C --> D[사용자 입력: 코드]
  D --> E[POST /api/verify]
  E --> F[JWT 발급]
  F --> G[POST /api/channels]
  G --> H[channels 테이블에 저장]
  H --> I[사용자(웹) 링크로 접속]
  I --> J[Socket.IO: joinChannel]
  J --> K[DB: channel_members 업데이트]
  K --> L[클라이언트: notesList 수신]
  L --> M[클라이언트: saveNote 이벤트]
  M --> N[DB: notes에 저장]
  N --> O[Socket.IO: noteAdded 브로드캐스트]
  O --> L

  subgraph E2E
    P[클라이언트: 키페어 생성] --> Q[POST /api/keys (JWT)]
    Q --> R[users.public_key 업데이트]
  end

  style E2E fill:#f9f,stroke:#333,stroke-width:1px
```

## 엔드포인트 요약

- `POST /api/register` — { contact, type } (데모: 코드 반환)
- `POST /api/verify` — { contact, type, code } → { token, userId }
- `POST /api/channels` — { name, limit } → { channelId, channelLink }
- `GET /api/channels/:id` — 채널 정보
- `POST /api/keys` — (Auth) { publicKey } 등록

프론트엔드 예시 및 파일:
- [frontend/index.html](frontend/index.html)
- [frontend/app.js](frontend/app.js)

DB 마이그레이션 파일:
- [backend/migrations/001_init.sql](backend/migrations/001_init.sql)

추가 노트
- 현재 인증 코드 전송(SMS/Email)은 데모 목적으로 동작하지 않으므로, 실제 서비스에서는 Twilio/SendGrid 등 외부 서비스를 연동하십시오.
- E2E 암호화는 공개키 등록과 클라이언트 키 생성 예시만 포함되어 있습니다. 메시지 본문을 완전한 E2E로 보호하려면 클라이언트에서 수신자의 공개키로 암호화하여 서버에 암호문을 저장/전달하는 추가 구현이 필요합니다.
# cert_messenger
cert_messenger
