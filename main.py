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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

# 라우터 임포트
from routes import tasks, edges

# 환경변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(title="Linkdo API")

# CORS 설정 - Vite 개발/프리뷰 서버 허용
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
    """서버 및 데이터베이스 상태 확인"""
    try:
        client.admin.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/api/graph")
def get_graph():
    """
    그래프 데이터 통합 조회 (tasks + edges)
    프론트엔드 초기 로딩 최적화용
    
    Returns:
        dict: { tasks: [...], edges: [...] }
    """
    # Tasks 조회
    tasks = list(tasks_collection.find())
    tasks_result = []
    for task in tasks:
        tasks_result.append({
            "id": task.get("id"),
            "title": task.get("title"),
            "description": task.get("description"),
            "priority": task.get("priority", "medium"),
            "status": task.get("status", "todo"),
            "category": task.get("category", "general"),
        })
    
    # Edges 조회
    edges = list(edges_collection.find())
    edges_result = []
    for edge in edges:
        edges_result.append({
            "id": edge.get("id"),
            "source": edge.get("source"),
            "target": edge.get("target"),
            "weight": edge.get("weight", 0.5),
        })
    
    return {"tasks": tasks_result, "edges": edges_result}


@app.delete("/api/tasks/{task_id}/cascade")
def delete_task_cascade(task_id: str):
    """
    태스크와 연결된 엣지를 함께 삭제
    
    Args:
        task_id: 삭제할 태스크의 ID
        
    Returns:
        dict: 삭제 결과 (삭제된 태스크, 엣지 수)
    """
    # 태스크 존재 확인
    task = tasks_collection.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다")
    
    # 연결된 엣지 삭제 (source 또는 target이 해당 태스크인 경우)
    edge_result = edges_collection.delete_many({
        "$or": [
            {"source": task_id},
            {"target": task_id}
        ]
    })
    
    # 태스크 삭제
    tasks_collection.delete_one({"id": task_id})
    
    return {
        "message": "태스크와 연결된 엣지가 삭제되었습니다",
        "task_id": task_id,
        "deleted_edges_count": edge_result.deleted_count
    }