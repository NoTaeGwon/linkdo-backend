"""
================================================================
파일명       : main.py
목적         : FastAPI 애플리케이션 진입점
설명         :
  - FastAPI 앱 인스턴스 생성 및 설정
  - CORS 미들웨어 설정 (프론트엔드 요청 허용)
  - MongoDB 연결 및 컬렉션 정의
  - 라우터 등록 (tasks, edges)
  - 기본 라우트 및 헬스체크 API
================================================================
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

# 라우터 임포트
from routes import tasks, edges

# 환경변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(title="Linkdo API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB 연결
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/linkdo")
client = MongoClient(MONGO_URI)
db = client["linkdo"]

# 컬렉션
tasks_collection = db["tasks"]
edges_collection = db["edges"]

# 라우터에 컬렉션 주입
tasks.set_collection(tasks_collection)
edges.set_collection(edges_collection)

# 라우터 등록
app.include_router(tasks.router)
app.include_router(edges.router)

@app.get("/")
async def root():
    return {"message": "Linkdo API is running"}

@app.get("/health")
def health_check():
    try:
        client.admin.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}