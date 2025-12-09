FROM python:3.10-slim

WORKDIR /app

# 기본 패키지 설치 (git, unzip, curl 등 필요시)
RUN apt-get update && apt-get install -y \
    awscli \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY . .

# entrypoint.sh 실행 권한 추가
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
