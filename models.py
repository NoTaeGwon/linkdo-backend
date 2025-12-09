"""
================================================================
파일명       : models.py
목적         : Pydantic 데이터 모델 정의
설명         :
  - TaskCreate: 새 태스크 생성 시 사용
  - TaskUpdate: 태스크 수정 시 사용 (부분 업데이트 지원)
  - TaskResponse: API 응답용 태스크 모델
  - EdgeCreate: 새 엣지 생성 시 사용
  - EdgeResponse: API 응답용 엣지 모델
  - Priority, Status: 열거형 타입 정의
================================================================
"""

from typing import Literal, Optional
from pydantic import BaseModel


# ============================================================
# 타입 정의
# ============================================================

Priority = Literal["low", "medium", "high", "critical"]
"""태스크 우선순위 타입. low < medium < high < critical 순으로 중요도 증가"""

Status = Literal["todo", "in-progress", "done"]
"""태스크 상태 타입. todo → in-progress → done 순으로 진행"""


# ============================================================
# Task 모델
# ============================================================

class TaskCreate(BaseModel):
    """
    새 태스크 생성 시 사용하는 모델
    
    Attributes:
        id: 태스크 고유 식별자 (클라이언트에서 생성)
        title: 태스크 제목 (필수)
        description: 태스크 설명 (선택)
        priority: 우선순위 (기본값: medium)
        status: 상태 (기본값: todo)
        category: 카테고리 (기본값: general)
    """
    id: str
    title: str
    description: Optional[str] = None
    priority: Priority = "medium"
    status: Status = "todo"
    category: str = "general"


class TaskUpdate(BaseModel):
    """
    태스크 수정 시 사용하는 모델
    
    Attributes:
        title: 태스크 제목
        description: 태스크 설명
        priority: 우선순위
        status: 상태
        category: 카테고리
    """
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    category: Optional[str] = None


class TaskResponse(BaseModel):
    """
    API 응답용 태스크 모델
    
    Attributes:
        id: 태스크 고유 식별자
        title: 태스크 제목
        description: 태스크 설명
        priority: 우선순위
        status: 상태
        category: 카테고리
    """
    id: str
    title: str
    description: Optional[str] = None
    priority: Priority
    status: Status
    category: str


# ============================================================
# Edge 모델
# ============================================================

class EdgeCreate(BaseModel):
    """
    새 엣지(태스크 간 연결) 생성 시 사용하는 모델
    
    Attributes:
        source: 시작 노드(태스크)의 ID
        target: 끝 노드(태스크)의 ID
        weight: 연관도 (0~1 사이 값, 기본값: 0.5)
    """
    source: str
    target: str
    weight: float = 0.5


class EdgeResponse(BaseModel):
    """
    API 응답용 엣지 모델
    
    Attributes:
        id: 엣지 고유 식별자 (자동 생성)
        source: 시작 노드(태스크)의 ID
        target: 끝 노드(태스크)의 ID
        weight: 연관도
    """
    id: int
    source: str
    target: str
    weight: float


