
FROM python:3.10.18-slim
#$TARGETPLATFORM << Docker가 자동으로 주입하는 환경 변수

# Install build dependencies for packages like pycairo (matplotlib dependency)
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc \
  g++ \
  pkg-config \
  libcairo2-dev \
  libpango1.0-dev \
  libffi-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
