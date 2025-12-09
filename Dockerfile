# ================================================================
# 파일명       : Dockerfile
# 목적         : Linkdo 백엔드 Docker 이미지 빌드
# 설명         :
#   - Python 3.11 slim 이미지 기반
#   - FastAPI + Uvicorn 서버 실행
# ================================================================

FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 서버 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

