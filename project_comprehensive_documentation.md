# Caffeine Project Deep Dive Analysis

**Date:** 2024-12-24
**Version:** 2.0 (Detailed Analysis)
**Target Audience:** System Architects, Senior Developers

---

## 1. System Architecture Deep Dive

Caffeine은 **Microservices Architecture (MSA)** 원칙을 따르며, 각 서비스는 Docker 컨테이너로 격리되어 오케스트레이션됩니다.

### 1.1. Container Orchestration Strategy
`docker-compose.yml`을 통해 정의된 5개의 주요 서비스가 `caf_network` 브리지 네트워크 내에서 통신합니다.

| Container | Internal Port | Host Port | Dependency | Description |
| :--- | :--- | :--- | :--- | :--- |
| `caf_backend` | 8000 | 8001 | DB | **Core API Gateway**. 모든 비즈니스 로직의 진입점. |
| `caf_front_admin` | 3000 | 3001 | Backend | Next.js 기반 **SSR** 웹 애플리케이션. |
| `caf_llm_analysis` | 9102 | 9102 | - | Google Gemini API를 래핑한 **AI Microservice**. |
| `caf_nginx` | 80 | 80 | Backend/Frontend | Reverse Proxy. SSL Termination 및 라우팅 담당. |
| **AWS RDS** | 5432 | - | - | 프로덕션 데이터베이스 (PostgreSQL). |

---

## 2. Backend Logic Analysis (`10_backend`)

FastAPI의 비동기 성능을 극대화하기 위해 `async/await` 패턴과 `AsyncSession`을 전면 도입했습니다.

### 2.1. Database Schema Design (`SQLAlchemy ORM`)

데이터 무결성과 성능을 고려한 정규화된 스키마를 사용합니다.

#### **User Model** (`models/user.py`)
사용자 인증 및 개인화 설정을 담당하는 핵심 엔티티입니다.
*   **Auth**: `email` (Unique), `password_hash` (Bcrypt), `social_provider` (OAuth).
*   **Settings**: `budget_limit` (월 예산), `budget_alert_enabled` (알림 트리거).
*   **Relationships**: `LoginHistory` (1:N), `Transaction` (1:N).

#### **Transaction Model** (`models/transaction.py`)
대용량 거래 데이터를 효율적으로 처리하기 위한 구조입니다.
*   **Optimization**: `user_id`와 `transaction_time`에 복합 인덱스(Composite Index)가 적용되어 시계열 조회 성능 최적화.
*   **Fields**: `merchant_name`, `amount`, `category_id`, `status` (completed/pending).

### 2.2. Complex API Logic Implementation

#### **Transaction Filtering Strategy** (`routers/transactions.py`)
`get_transactions` API는 단일 엔드포인트에서 복합 필터링을 지원하기 위해 **Dynamic Query Building** 패턴을 사용합니다.

```python
# Dynamic Filtering Example
conditions = []
if start_date: 
    conditions.append(Transaction.transaction_time >= start_dt)
if search:
    # OR 조건을 통한 유연한 검색 (가맹점명 OR 메모)
    conditions.append(or_(
        Transaction.merchant_name.ilike(f"%{search}%"),
        Transaction.description.ilike(f"%{search}%")
    ))

# 쿼리 실행 시 조건을 Unpacking하여 적용
query = query.where(and_(*conditions))
```

#### **Bulk Insert & Validation** (`routers/transactions.py`)
대량의 거래 내역(엑셀 업로드 등) 처리를 위해 `TransactionBulkCreate` 스키마를 사용하며, 실패 용인(Fault Tolerance) 로직이 포함되어 있습니다.
*   **Category Logic**: 입력된 카테고리가 DB에 없으면 자동으로 '기타' 카테고리 ID를 매핑하거나 기본값을 할당하여 에러를 방지합니다.
*   **Date Fallback**: 날짜 형식이 올바르지 않으면 랜덤한 과거 날짜를 할당하거나 현재 시간을 사용하는 Heuristic Fallback 로직이 적용되어 있습니다.

---

## 3. Frontend Architecture Analysis

### 3.1. User App (`20_frontend_user`) - React Native
모바일 환경에서의 사용자 경험(UX) 최적화에 초점을 맞췄습니다.

#### **Context-Driven State Management**
Redux 대신 가벼운 **Context API**를 사용하여 보일러플레이트를 줄였습니다.
*   **AuthContext**: `login(token)`, `logout()`, `user` 객체를 전역 공급. 앱 시작 시 `AsyncStorage`에서 토큰을 복원하여 자동 로그인 구현.
*   **ThemeContext**: 다크 모드/라이트 모드 전환을 즉시 반영하며, 모든 컴포넌트가 `colors` 객체를 구독하여 스타일을 동적으로 적용.

### 3.2. Admin Dashboard (`21_frontend_admin`) - Next.js 16
데이터 시각화와 운영 효율성에 중점을 둔 웹 애플리케이션입니다.

#### **Frontend-Side Data Aggregation**
서버 부하를 줄이기 위해, Raw Data를 한 번 가져온 후 클라이언트(`AdminIntegratedAnalysis.jsx`)에서 `useMemo`를 통해 실시간으로 집계합니다.
*   **Category Aggregation**: 거래 내역 배열을 순회하며 카테고리별 합계를 계산 (`O(N)`).
*   **Benefit**: 사용자가 필터(날짜, 검색어)를 변경할 때마다 API를 다시 호출하지 않고 즉시 차트가 갱신됩니다.

---

## 4. AI & LLM Service Analysis (`51_llm_analysis`)

비싼 LLM API 비용과 응답 지연 시간을 최소화하기 위한 **지능형 캐싱 레이어**가 핵심입니다.

### 4.1. In-Memory Caching Strategy
`app.py`에 구현된 캐싱 로직은 동일한 질문에 대해 모델 호출을 건너뜁니다.
*   **Key Generation**: 프롬프트 문자열의 **MD5 Hash**를 키로 사용.
*   **TTL (Time-To-Live)**: 300초(5분) 동안 유효. 최근 대화 맥락이 유지되는 동안 빠른 응답 보장.
*   **Eviction Policy**: 메모리 오버플로우 방지를 위해 최대 100개의 키만 저장하고 오래된 항목부터 삭제(LRU).

### 4.2. Prompt Engineering (Persona)
'잠깐만AI'라는 페르소나를 부여하여 사용자의 소비 습관을 교정합니다.
*   **Tone**: "팩트폭행", "반말", "비꼬기/칭찬"을 섞은 매운맛 조언.
*   **Context Injection**: 단순 질문뿐만 아니라 사용자의 **예산 소진율**, **최근 거래 내역**, **상위 지출 카테고리** 데이터를 프롬프트에 동적으로 삽입하여 개인화된 답변을 생성합니다.

---

## 5. Security & Infrastructure

### 5.1. Authentication Flow
1.  **Client**: 로그인 시도 (`/api/users/login`) -> `OAuth2PasswordRequestForm` 데이터 전송.
2.  **Backend**: `verify_password`로 해시 검증 -> `create_access_token`으로 JWT 생성 (HS256 알고리즘).
3.  **Middleware**: 이후 모든 요청 헤더의 `Authorization: Bearer <token>`을 `verify_access_token` 함수가 가로채서 복호화 및 유효성 검증 (`routers/user.py`의 `Auth_Dependency`).

### 5.2. Network Security
*   **Rate Limiting**: `slowapi`를 사용하여 `/health` 등 공개 엔드포인트에 IP 기반 요청 제한(10/minute)을 걸어 DDoS 공격 완화.
*   **CORS Policy**: `LOCAL_ORIGINS` (localhost, 127.0.0.1) 및 프로덕션 도메인만 엄격하게 허용.
*   **Security Headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` 등 보안 헤더 강제 적용 미들웨어 가동.

---

## 6. 결론 및 제언 (Conclusion)

본 프로젝트는 **데이터의 흐름(Data Flow)**이 명확하게 설계되어 있습니다.
Backend가 신뢰할 수 있는 구심점(Single Source of Truth) 역할을 하며, Frontend는 각 플랫폼(Mobile, Web)에 맞는 최적화된 UX를 제공하고, AI 서비스는 보조적인 인텔리전스를 제공하는 구조입니다.

향후 발전 방향으로는 **Redis**를 도입하여 로컬 메모리 캐시를 분산 캐시로 업그레이드하고, **Celery**를 통해 대량 트랜잭션 처리를 비동기 큐 작업으로 전환하는 것을 제안합니다.
