"""
================================================================
파일명       : routes/edges.py
목적         : Edges API 라우터
설명         :
    GET    /api/edges                   - 전체 엣지 조회
    POST   /api/edges                   - 새 엣지 생성
    DELETE /api/edges/{source}/{target} - 엣지 삭제
================================================================
"""

from fastapi import APIRouter, HTTPException
from models import EdgeCreate, EdgeResponse

# 라우터 생성
router = APIRouter(prefix="/api/edges", tags=["edges"])

# MongoDB 컬렉션
edges_collection = None


def set_collection(collection):
    """
    MongoDB 컬렉션을 주입받는 함수
    
    Args:
        collection: MongoDB edges 컬렉션 객체
    """
    global edges_collection
    edges_collection = collection

@router.get("/", response_model=list[EdgeResponse])
def get_all_edges():
    """
    전체 엣지 목록을 조회
    
    Returns:
        list[EdgeResponse]: 모든 엣지 목록
    """
    edges = list(edges_collection.find())
    result = []

    for edge in edges:
        edge_dict = {
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
    # 엣지 중복 연결 체크
    existing = edges_collection.find_one({
        "source": edge.source,
        "target": edge.target
    })
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 연결입니다")

    edge_dict = edge.model_dump()
    edges_collection.insert_one(edge_dict)
    return edge_dict

@router.delete("/{source}/{target}")
def delete_edge(source: str, target: str):
    """
    엣지를 삭제

    Args:
        source: 시작 노드(태스크) ID
        target: 끝 노드(태스크) ID
    
    Returns:
        dict: 삭제 결과 메시지
    
    Raises:
        HTTPException: 엣지가 존재하지 않을 때 (404)
    """
    result = edges_collection.delete_one({"source": source, "target": target})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="엣지를 찾을 수 없습니다")
    return {"message": "엣지가 삭제되었습니다", "source": source, "target": target}
