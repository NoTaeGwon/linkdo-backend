"""
================================================================
파일명       : routes/edges.py
목적         : Edges API 라우터
설명         :
    GET    /api/edges       - 전체 엣지 조회
    POST   /api/edges       - 새 엣지 생성
    DELETE /api/edges/{id}  - 엣지 삭제
================================================================
"""

from fastapi import APIRouter, HTTPException
from typing import List
from models import EdgeCreate, EdgeResponse

# 라우터 생성
router = APIRouter(prefix="/api/edges", tags=["edges"])

# MongoDB 컬렉션
edges_collection = None
edge_counter = 0    # 자동 증가 ID용

def set_collection(collection):
    """
    MongoDB 컬렉션을 주입받는 함수
    
    Args:
        collection: MongoDB edges 컬렉션 객체
    """
    global edges_collection, edge_counter
    edges_collection = collection
    # 기존 엣지 중 가장 큰 ID 찾기
    last_edge = edges_collection.find_one(sort=[("id", -1)])
    edge_counter = (last_edge.get("id") + 1) if last_edge else 1

@router.get("/", response_model=List[EdgeResponse])
def get_all_edges():
    """
    전체 엣지 목록을 조회
    
    Returns:
        List[EdgeResponse]: 모든 엣지 목록
    """
    edges = list(edges_collection.find())
    result = []

    for edge in edges:
        edge_dict = {
            "id": edge.get("id"),
            "source": edge.get("source"),
            "target": edge.get("target"),
            "weight": edge.get("weight", 0.5),
        }
        result.append(edge_dict)
    return result

@router.post("/", response_model=EdgeResponse)
def create_edge(edge: EdgeCreate):
    """
    새 엣지를 생성

    Args:
        edge: 생성할 엣지 정보
    
    Returns:
        EdgeResponse: 생성된 엣지 정보
    """
    global edge_counter

    # 엣지 중복 연결 체크
    existing = edges_collection.find_one({
        "source": edge.source,
        "target": edge.target
    })
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 연결입니다")

    edge_dict = edge.model_dump()
    edge_dict["id"] = edge_counter
    edge_counter += 1

    edges_collection.insert_one(edge_dict)
    return edge_dict

@router.delete("/{edge_id}")
def delete_edge(edge_id: int):
    """
    엣지를 삭제

    Args:
        edge_id: 삭제할 엣지의 ID
    
    
    Returns:
        dict: 삭제 결과 메시지
    
    Raises:
        HTTPException: 엣지가 존재하지 않을 때 (404)
    """
    result = edges_collection.delete_one({"id": edge_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="엣지를 찾을 수 없습니다")
    return {"message": "엣지가 삭제되었습니다", "id": edge_id}
