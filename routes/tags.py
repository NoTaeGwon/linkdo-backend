"""
================================================================
파일명       : routes/tags.py
목적         : Tags API 라우터
설명         :
    GET    /api/tags              - 전체 태그 목록 조회
    POST   /api/tags/suggest-tags - LLM 태그 추천
================================================================
"""

import os
from google import genai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 라우터 생성
router = APIRouter(prefix="/api/tags", tags=["tags"])

# MongoDB 컬렉션
tasks_collection = None

# Gemini 클라이언트
gemini_client = None


def set_collection(collection):
    """
    MongoDB 컬렉션을 주입받는 함수.
    
    Args:
        collection: MongoDB tasks 컬렉션 객체
    """
    global tasks_collection
    tasks_collection = collection


def set_gemini_client(client):
    """
    Gemini 클라이언트를 주입받는 함수.
    
    Args:
        client: genai.Client 객체
    """
    global gemini_client
    gemini_client = client


class TagSuggestionRequest(BaseModel):
    """태그 추천 요청 모델"""
    title: str
    description: str = ""


@router.get("/")
def get_tags():
    """
    전체 태그 목록 조회 (모든 테스크에서 unique 태그 추출)

    Returns:
        list[str]: 정렬된 태그 목록
    """
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags"}},
        {"$sort": {"_id": 1}},
    ]

    result = tasks_collection.aggregate(pipeline)
    return [doc["_id"] for doc in result]


@router.post("/suggest-tags")
async def suggest_tags(request: TagSuggestionRequest):
    """
    LLM을 이용한 태그 추천

    Args:
        request: 테스크 제목과 설명
    
    Returns:
        dict: 추천 태그 목록
    """
    if not gemini_client:
        raise HTTPException(status_code=500, detail="Gemini API 키가 설정되지 않았습니다")

    # 기존 태그 목록 가져오기
    existing_tags = get_tags()

    # 프롬프트 생성
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
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        # 응답 파싱
        tags_text = response.text.strip()
        tags = [tag.strip() for tag in tags_text.split(",")]
        tags = [tag for tag in tags if tag]  # 빈 태그 제거

        return {"tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"태그 추천 실패: {str(e)}")

