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
import math
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel

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

# Gemini 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class TagSuggestionRequest(BaseModel):
    """태그 추천 요청 모델"""
    title: str
    description: str = ""

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
            "tags": task.get("tags", []),
        })
    
    # Edges 조회
    edges = list(edges_collection.find())
    edges_result = []
    for edge in edges:
        edges_result.append({
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


@app.get("/api/tags")
def get_tags():
    """
    전체 태그 목록 조회 (모든 테스크에서 unique 태그 추출)

    Returns:
        list[str]: 정렬된 태그 목록
    """
    pipline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags"}},
        {"$sort": {"_id": 1}},
    ]

    result = tasks_collection.aggregate(pipline)
    return [doc["_id"] for doc in result]

@app.post("/api/tags/suggest-tags")
async def suggest_tags(request: TagSuggestionRequest):
    """
    LLM을 이용한 태그 추천

    Args:
        request: 테스크 제목과 설명
    
    Returns:
        dist: 추천 태그 목록
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API 키가 설정되지 않았습니다")

    # 기존 태그 목록 가져오기
    existing_tags = get_tags()

    # 프롬포트 생성
    prompt = f"""당신은 할 일(Task) 관리 앱의 태그 추천 시스템입니다.

사용자가 입력한 할 일에 적절한 태그를 3~5개 추천해주세요.

기존에 사용중인 태그 목록: {existing_tags if existing_tags else "없음"}

할 일 제목: {request.title}
할 일 설명: {request.description if request.description else "없음"}

규칙:
1. 기존 태그가 있다면 최대한 기존 태그를 활용하세요
2. 새로운 태그가 필요하면 간결하고 명확한 한글 태그를 만드세요
3. 태그는 쉼표로 구분해서 출력하세요
4. 태그만 출력하고 다른 설명은 하지 마세요

예시 출력: 업무, 회의, 중요"""
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        
        # 응답 파싱
        tags_text = response.text.strip()
        tags = [tag.strip() for tag in tags_text.split(",")]
        tags = [tag for tag in tags if tag] # 빈 태그 제거

        return {"tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"태그 추천 실패: {str(e)}")


def get_embedding(text: str) -> list[float]:
    """
    텍스트를 임베딩 벡터로 변환

    Args:
        text: 변환할 텍스트
    
    Returns:
        list[float]: 임베딩 백터
    """
    if not GEMINI_API_KEY:
        return []

    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
        )
        return result['embedding']
    except Exception as e:
        print(f"임베딩 생성 실패: {e}")
        return []


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    두 백터 간의 코사인 유사도 개산

    Args:
        vec1: 첫 번째 백터
        vec2: 두 번째 백터

    Returns:
        float: 유사도 (-1 ~ 1, 1에 가까울수록 유사)
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))    # zip: 두 리스트를 짝지어 주는 함수수
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0: 
        return 0.0

    return dot_product / (magnitude1 * magnitude2)

@app.get("/api/tasks/{task_id}/similar")
def get_similar_tasks(task_id: str, limit: int = 5):
    """
    유사한 테스크 찾기

    Args:
        task_id: 기준 테스크 ID
        limit: 반환할 유사한 테스크 최대 개수 (기본값: 5)
    
    Returns:
        list: 유사도 순으로 정렬된 테스크 목록
    """
    # 기준 테스크 조회
    target_task = tasks_collection.find_one({"id": task_id})
    if not target_task:
        raise HTTPException(status_code=404, detail="테스크를 찾을 수 없습니다")
    
    target_embedding = target_task.get("embedding", [])
    if not target_embedding:
        raise HTTPException(status_code=400, detail="임베딩 정보가 없는 테스크입니다.")
    
    # 모든 테스크와 유사도 계산
    all_tasks = list(tasks_collection.find({"id": {"$ne": task_id}}))   # $ne: 같지 않은 쿼리

    similarities = []
    for task in all_tasks:
        task_embedding = task.get("embedding", [])
        if task_embedding:
            similarity = cosine_similarity(target_embedding, task_embedding)
            similarities.append({
                "id": task.get("id"),
                "title": task.get("title"),
                "description": task.get("description"),
                "priority": task.get("priority", "medium"),
                "status": task.get("status", "todo"),
                "category": task.get("category", "general"),
                "tags": task.get("tags", []),
                "similarity": round(similarity, 4)
            })

    # 유사도 높은 순으로 정렬
    similarities.sort(key=lambda x: x["similarity"], reverse=True)

    return similarities[:limit]

