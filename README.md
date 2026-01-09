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
