-- 기존 테이블이 있다면 삭제
DROP TABLE IF EXISTS users CASCADE;

-- 2. Users (수정된 스키마: is_superuser 포함)
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(100) NOT NULL,
    nickname        VARCHAR(50),
    phone           VARCHAR(20),
    
    -- 권한 관리
    role            VARCHAR(20) NOT NULL DEFAULT 'USER',
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    
    social_provider VARCHAR(20),
    social_id       VARCHAR(255),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

-- 3. 관리자 계정 강제 삽입
INSERT INTO users (
    email, 
    password_hash, 
    name, 
    role, 
    is_superuser, 
    is_active
) VALUES (
    'admin@caffeine.com', 
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- 로그인 비밀번호 : secret
    '시스템관리자', 
    'ADMIN', 
    TRUE, 
    TRUE
);
