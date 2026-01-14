<div align="center">

# ☕ Caffeine

### **"A DROP OF DATA, A SHOT OF INSIGHT"**

AI 기반 소비 패턴 분석 및 이상 거래 탐지 플랫폼

[![Deploy Status](https://img.shields.io/badge/deploy-live-brightgreen?style=flat-square)](https://caffeineai.net)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React Native](https://img.shields.io/badge/React_Native-0.81-61DAFB?style=flat-square&logo=react)](https://reactnative.dev/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![AWS](https://img.shields.io/badge/AWS-ECS_Fargate-FF9900?style=flat-square&logo=amazon-aws)](https://aws.amazon.com/)

[Live Demo](https://caffeineai.net) · [Admin Dashboard](https://admin.caffeineai.net) · [API Docs](https://api.caffeineai.net/docs)

</div>

---

## 📌 프로젝트 소개

**Caffeine**은 개인 소비자의 거래 데이터를 분석하여 소비 패턴을 파악하고, 다음 소비를 예측하며, 이상 거래를 실시간으로 탐지하는 AI 기반 금융 분석 플랫폼입니다.

### 🎯 해결하고자 한 문제

| 문제점 | 솔루션 |
|--------|--------|
| 소비자가 본인의 소비 패턴을 정확히 파악하기 어려움 | ML 기반 소비 분석 및 카테고리별 통계 제공 |
| 이상 거래(사기)에 취약하고 사후 대응만 가능 | XGBoost + 휴리스틱 기반 실시간 이상 거래 탐지 |
| 기존 가계부 앱은 단순 기록만 제공 | LLM 기반 맞춤형 인사이트 리포트 자동 생성 |

---

## ✨ 주요 기능

### 🔮 다음 거래 예측 (ML)
- XGBoost 모델 기반 다음 소비 카테고리 예측
- Feature Engineering: 시간대, 요일, 카테고리, 금액 정규화
- **정확도: 73.47%**

### 🚨 이상 거래 탐지 (Fraud Detection)
- ML 모델 + 휴리스틱 규칙 결합 (Hybrid Approach)
- 평균 지출 100배 초과 시 자동 탐지
- 카테고리별 컷오프 기준 적용 (Cold Start 대응)

### 💬 AI 챗봇 (잔소리 시스템)
- Google Gemini 2.0 Flash API 기반
- 거래 금액별 차별화된 페르소나
- 실시간 소비 상담 및 개선 팁 제공

### 📊 AI 소비 분석 리포트
- LLM 기반 주간/월간/일간 리포트 자동 생성
- PDF 생성 (ReportLab) + HTML 슬라이드 덱
- APScheduler 기반 이메일 자동 발송

### 👔 관리자 대시보드
- 전체 사용자 연령대/성별 소비 통계
- Recharts 기반 인터랙티브 시각화
- 이상 거래 관리 및 리포트 발송

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AWS CloudFront (CDN)                                   │
│   caffeineai.net (User)  │  admin.caffeineai.net (Admin)  │  api.caffeineai.net │
└─────────────────────────────────────────────────────────────────────────────────┘
               │                         │                         │
               ▼                         ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────────────────┐
│      S3 Bucket       │  │      S3 Bucket       │  │  Application Load Balancer  │
│  (React Native/Expo) │  │  (Next.js Static)    │  │           (ALB)             │
└──────────────────────┘  └──────────────────────┘  └──────────────┬──────────────┘
                                                                    │
                                                                    ▼
                                                   ┌─────────────────────────────┐
                                                   │     AWS ECS Fargate         │
                                                   │     Docker Container        │
                                                   │     (FastAPI Backend)       │
                                                   └──────────────┬──────────────┘
                                                                  │
                    ┌─────────────────────────────────────────────┼─────────────────┐
                    │                                             │                 │
                    ▼                                             ▼                 ▼
      ┌─────────────────────────┐             ┌─────────────────────────┐  ┌───────────────────┐
      │     AWS RDS             │             │     XGBoost ML Model    │  │  Google Gemini    │
      │     PostgreSQL          │             │     (예측 / Fraud)       │  │  API (LLM)        │
      └─────────────────────────┘             └─────────────────────────┘  └───────────────────┘
```

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| **Backend** | FastAPI, SQLAlchemy 2.0 (Async), Pydantic v2, APScheduler, Uvicorn |
| **Frontend (User)** | React Native, Expo, Victory Native, React Navigation |
| **Frontend (Admin)** | Next.js 16, TypeScript, Tailwind CSS v4, Recharts |
| **Database** | PostgreSQL (AWS RDS), AsyncPG |
| **ML/AI** | XGBoost, Scikit-learn, Pandas, NumPy |
| **LLM** | Google Gemini 2.0 Flash API |
| **인증** | JWT (python-jose), OAuth2 (Google/Kakao), Bcrypt |
| **보안** | Fernet 암호화, Rate Limiting (SlowAPI), Security Headers |
| **Email** | aiosmtplib, Jinja2 Template, ReportLab (PDF) |
| **DevOps** | Docker, GitHub Actions, AWS (ECR, ECS, S3, CloudFront, RDS, ALB) |

---

## 🚀 CI/CD 파이프라인

### Backend (ECS Fargate)
```
Push to main → GitHub Actions → OIDC Auth → Docker Build → ECR Push → ECS Deploy
```

### Frontend (S3 + CloudFront)
```
Push to main → GitHub Actions → npm build → S3 Sync → CloudFront Invalidation
```

**주요 특징:**
- OIDC 기반 AWS 인증 (Access Key 없이 보안 인증)
- 환경변수는 GitHub Secrets → ECS Task Definition 주입
- 경로 기반 독립 파이프라인 (Frontend/Backend 분리)

---

## 📁 프로젝트 구조

```
caffeine/
├── 00_docs_core/              # 문서, ERD, API 명세
├── 10_backend/                # FastAPI 백엔드
│   ├── app/
│   │   ├── core/              # 환경설정, 보안, 미들웨어
│   │   ├── db/                # Database (Model, Schema, CRUD)
│   │   ├── routers/           # API 라우터
│   │   └── services/          # 비즈니스 로직
│   ├── Dockerfile
│   └── requirements.txt
├── 20_frontend_user/          # React Native (Expo) 사용자 앱
├── 21_frontend_admin/         # Next.js 관리자 대시보드
├── 30_nginx/                  # 로컬 테스트용 Reverse Proxy
├── .github/workflows/         # GitHub Actions CI/CD
├── docker-compose.yml         # 로컬 개발 환경
└── ecs-task-definition.json   # AWS ECS 배포 설정
```

---

## 🖥️ 실행 방법

### 로컬 개발 환경 (Docker)

```bash
# 1. 저장소 클론
git clone https://github.com/your-repo/caffeine.git
cd caffeine

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에 필요한 값 입력 (DB, API Keys 등)

# 3. Docker Compose 실행
docker-compose up --build

# 4. 접속
# Backend API: http://localhost:8001/docs
# Admin Dashboard: http://localhost:3001
```

---

## 📊 주요 성과

- **ML 예측 정확도**: 73.47% (XGBoost 기반 6개 카테고리 분류)
- **실제 운영 배포**: AWS ECS Fargate + CloudFront (caffeineai.net)
- **완전 자동화 CI/CD**: OIDC 기반 보안 인증, Zero-downtime 배포
- **Dev = Prod 환경**: Docker 컨테이너 기반 환경 동일성 보장

---

## 📅 프로젝트 기간

**2025.11.17 ~ 2026.05**

---

## 📝 라이선스

This project is licensed under the MIT License.
