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
from datetime import datetime
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
        tags: 태그 (필수)
        due_date: 마감일 (선택)
    """
    id: str
    title: str
    description: Optional[str] = None
    priority: Priority = "medium"
    status: Status = "todo"
    category: str = "general"
    tags: list[str] = []
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    """
    태스크 수정 시 사용하는 모델
    
    Attributes:
        title: 태스크 제목
        description: 태스크 설명
        priority: 우선순위
        status: 상태
        category: 카테고리
        tags: 태그
        due_date: 마감일
    """
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    due_date: Optional[datetime] = None

class TaskResponse(BaseModel):
    """
    API 응답용 태스크 모델
    
    Attributes:
        workspace_id: 워크스페이스 고유 식별자
        id: 태스크 고유 식별자
        title: 태스크 제목
        description: 태스크 설명
        priority: 우선순위
        status: 상태
        category: 카테고리
        tags: 태그
        due_date: 마감일
        x: PCA 계산된 X 좌표
        y: PCA 계산된 Y 좌표
    """
    workspace_id: str
    id: str
    title: str
    description: Optional[str] = None
    priority: Priority
    status: Status
    category: str
    tags: list[str]
    embedding: list[float] = []
    due_date: Optional[datetime] = None
    x: float = 0.0
    y: float = 0.0

# ============================================================
# Edge 모델
# ============================================================

# ============================================================
# Sync 모델
# ============================================================

class TaskSync(BaseModel):
    """
    동기화용 태스크 모델 (upsert 지원)
    
    Attributes:
        id: 태스크 고유 식별자
        title: 태스크 제목 (deleted=True일 때 빈 문자열 허용)
        description: 태스크 설명
        priority: 우선순위
        status: 상태
        category: 카테고리
        tags: 태그
        due_date: 마감일
        updated_at: 마지막 수정 시간 (충돌 해결용)
        deleted: 삭제 여부 (soft delete)
    """
    id: str
    title: Optional[str] = ""  # deleted=True일 때 빈 문자열 허용
    description: Optional[str] = None
    priority: Optional[Priority] = "medium"
    status: Optional[Status] = "todo"
    category: Optional[str] = "general"
    tags: list[str] = []
    due_date: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted: bool = False


class EdgeSync(BaseModel):
    """
    동기화용 엣지 모델
    
    Attributes:
        source: 시작 노드 ID
        target: 끝 노드 ID
        weight: 연관도
        deleted: 삭제 여부
    """
    source: str
    target: str
    weight: float = 0.5
    deleted: bool = False


class SyncRequest(BaseModel):
    """
    동기화 요청 모델
    
    Attributes:
        tasks: 동기화할 태스크 목록
        edges: 동기화할 엣지 목록
        last_sync_at: 마지막 동기화 시간
    """
    tasks: list[TaskSync] = []
    edges: list[EdgeSync] = []
    last_sync_at: Optional[datetime] = None


class SyncResponse(BaseModel):
    """
    동기화 응답 모델
    
    Attributes:
        tasks: 서버의 최신 태스크 목록
        edges: 서버의 최신 엣지 목록
        sync_stats: 동기화 통계
        synced_at: 동기화 완료 시간
    """
    tasks: list[TaskResponse]
    edges: list["EdgeResponse"]
    sync_stats: dict
    synced_at: datetime


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
        workspace_id: 워크스페이스 고유 식별자
        source: 시작 노드(태스크)의 ID
        target: 끝 노드(태스크)의 ID
        weight: 연관도
    """
    workspace_id: str
    source: str
    target: str
    weight: float


