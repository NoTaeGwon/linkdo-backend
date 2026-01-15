"""
================================================================
파일명       : main.py
목적         : FastAPI 애플리케이션 진입점
설명         :
  - FastAPI 앱 인스턴스 생성 및 설정
  - CORS 미들웨어 설정 (프론트엔드 요청 허용)
  - MongoDB 연결 및 컬렉션 정의
  - 라우터 등록 (tasks, edges, tags, graph)
  - 기본 라우트 및 헬스체크 API
================================================================
"""

import os
import logging
from google import genai
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 라우터 임포트
from routes import tasks, edges, tags, graph

# 환경변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(title="Linkdo API")

# 프록시 헤더 미들웨어 추가 (개발/디버깅용)
@app.middleware("http")
async def log_proxy_headers(request: Request, call_next):
    logger.info(f"Request path: {request.url.path}")
    logger.info(f"Request headers: {request.headers}")
    response = await call_next(request)
    return response

# CORS 설정 - 개발 서버 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "http://localhost:4173",  # Vite preview
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# MongoDB 연결
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/linkdo")
client = MongoClient(MONGO_URI)
db = client["linkdo"]

# 컬렉션
tasks_collection = db["tasks"]
edges_collection = db["edges"]

# 라우터에 컬렉션/클라이언트 주입
tasks.set_collections(tasks_collection, edges_collection)
edges.set_collection(edges_collection)
tags.set_collection(tasks_collection)
tags.set_gemini_client(gemini_client)
graph.set_collections(tasks_collection, edges_collection)

# 라우터 등록
app.include_router(tasks.router)
app.include_router(edges.router)
app.include_router(tags.router)
app.include_router(graph.router)


@app.get("/")
async def root(request: Request):
    """루트 엔드포인트 - API 상태 확인 및 헤더 로깅"""
    logger.info(f"Root endpoint hit. Headers: {request.headers}")
    return {"message": "Linkdo API is running"}


@app.get("/health")
def health_check():
    """서버 및 데이터베이스 상태 확인"""
    try:
        client.admin.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/debug/gemini")
def debug_gemini():
    """[임시] Gemini 클라이언트 상태 확인"""
    return {
        "api_key_exists": bool(GEMINI_API_KEY),
        "api_key_preview": GEMINI_API_KEY[:10] + "..." if GEMINI_API_KEY else None,
        "client_initialized": gemini_client is not None,
    }


def get_embedding(text: str) -> list[float]:
    """
    텍스트를 임베딩 벡터로 변환
    (tasks.py에서 import하여 사용)

    Args:
        text: 변환할 텍스트
    
    Returns:
        list[float]: 임베딩 벡터
    """
    if not gemini_client:
        return []

    try:
        result = gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"임베딩 생성 실패: {e}")
        return []
