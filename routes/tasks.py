"""
================================================================
파일명       : routes/tasks.py
목적         : Tasks API 라우터
설명         :
    GET    /api/tasks              - 전체 태스크 조회
    GET    /api/tasks/{id}         - 특정 태스크 조회
    POST   /api/tasks              - 새 태스크 생성
    POST   /api/tasks/sync         - 오프라인 동기화 (bulk upsert)
    PATCH  /api/tasks/{id}         - 태스크 부분 수정
    DELETE /api/tasks/{id}         - 태스크 삭제
    DELETE /api/tasks/{id}/cascade - 태스크 + 연결된 엣지 삭제
================================================================
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header
from models import TaskCreate, TaskUpdate, TaskResponse, SyncRequest, SyncResponse, TaskSync, EdgeResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

tasks_collection = None
edges_collection = None


def set_collections(tasks_col, edges_col):
    """
    MongoDB 컬렉션들을 주입받는 함수.
    
    Args:
        tasks_col: MongoDB tasks 컬렉션 객체
        edges_col: MongoDB edges 컬렉션 객체
    """
    global tasks_collection, edges_collection
    tasks_collection = tasks_col
    edges_collection = edges_col


@router.get("/", response_model=list[TaskResponse])
def get_all_tasks(
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
    tag: Optional[str] = None
):
    """
    전체 태스크 목록을 조회합니다.

    Args:
        x_workspace_id: 워크스페이스 고유 식별자 (헤더)
        tag: 필터링할 태그(선택)
    
    Returns:
        list[TaskResponse]: 모든 태스크 목록
    """
    workspace_id = x_workspace_id
    
    # 태그 필터링
    query = {"workspace_id": workspace_id}
    if tag:
        query["tags"] = tag

    tasks = list(tasks_collection.find(query))
    result = []
    for task in tasks:
        task_dict = {
            "workspace_id": task.get("workspace_id"),
            "id": task.get("id"),
            "title": task.get("title"),
            "description": task.get("description"),
            "priority": task.get("priority", "medium"),
            "status": task.get("status", "todo"),
            "category": task.get("category", "general"),
            "tags": task.get("tags", []),
            "embedding": task.get("embedding", []),
            "due_date": task.get("due_date"),
        }
        result.append(task_dict)
    return result


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
):
    """
    특정 태스크를 조회합니다.
    
    Args:
        task_id: 조회할 태스크의 ID
        x_workspace_id: 워크스페이스 고유 식별자 (헤더)
        
    Returns:
        TaskResponse: 태스크 정보
        
    Raises:
        HTTPException: 태스크가 존재하지 않을 때 (404)
    """
    workspace_id = x_workspace_id
    
    task = tasks_collection.find_one({"id": task_id, "workspace_id": workspace_id})
    if not task:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다")
    return {
        "workspace_id": task.get("workspace_id"),
        "id": task.get("id"),
        "title": task.get("title"),
        "description": task.get("description"),
        "priority": task.get("priority", "medium"),
        "status": task.get("status", "todo"),
        "category": task.get("category", "general"),
        "tags": task.get("tags", []),
        "embedding": task.get("embedding", []),
        "due_date": task.get("due_date"),
    }


@router.post("/", response_model=TaskResponse)
def create_task(
    task: TaskCreate,
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
):
    """
    새 태스크를 생성합니다.
    동일한 태그를 가진 기존 태스크들과 엣지를 자동 연결합니다.
    
    Args:
        task: 생성할 태스크 정보
        x_workspace_id: 워크스페이스 고유 식별자 (헤더)
        
    Returns:
        TaskResponse: 생성된 태스크 정보
        
    Raises:
        HTTPException: 이미 존재하는 ID일 때 (400)
    """
    workspace_id = x_workspace_id
    
    if tasks_collection.find_one({"id": task.id, "workspace_id": workspace_id}):
        raise HTTPException(status_code=400, detail="이미 존재하는 ID입니다")
    
    task_dict = task.model_dump()
    task_dict["workspace_id"] = workspace_id

    # 임베딩 생성 (제목 + 설명 + 태그)
    text_for_embedding = f"{task.title} {task.description or ''} {' '.join(task.tags)}"
    from main import get_embedding
    task_dict["embedding"] = get_embedding(text_for_embedding)
    
    tasks_collection.insert_one(task_dict)
    
    # 태그 기반 엣지 자동 연결
    if task.tags:
        # 동일 태그를 가진 기존 태스크 찾기 (같은 워크스페이스 내에서)
        existing_tasks = tasks_collection.find({
            "workspace_id": workspace_id,
            "id": {"$ne": task.id},  # 자기 자신 제외
            "tags": {"$in": task.tags}  # 태그 중 하나라도 일치
        })
        
        for existing_task in existing_tasks:
            # 공통 태그 수에 따라 weight 계산 (0.0 ~ 1.0)
            common_tags = set(task.tags) & set(existing_task.get("tags", []))
            weight = len(common_tags) / max(len(task.tags), len(existing_task.get("tags", [])))
            
            # 엣지 생성 (중복 방지 - 같은 워크스페이스 내에서)
            edge_exists = edges_collection.find_one({
                "workspace_id": workspace_id,
                "$or": [
                    {"source": task.id, "target": existing_task["id"]},
                    {"source": existing_task["id"], "target": task.id}
                ]
            })
            
            if not edge_exists:
                edges_collection.insert_one({
                    "workspace_id": workspace_id,
                    "source": task.id,
                    "target": existing_task["id"],
                    "weight": round(weight, 2)
                })
    
    return task_dict


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    task_update: TaskUpdate,
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
):
    """
    태스크를 부분 수정합니다.
    
    Args:
        task_id: 수정할 태스크의 ID
        task_update: 수정할 필드들 (None이 아닌 필드만 적용)
        x_workspace_id: 워크스페이스 고유 식별자 (헤더)
        
    Returns:
        TaskResponse: 수정된 태스크 정보
        
    Raises:
        HTTPException: 태스크가 존재하지 않을 때 (404)
    """
    workspace_id = x_workspace_id
    
    existing = tasks_collection.find_one({"id": task_id, "workspace_id": workspace_id})
    if not existing:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다")
    
    # None이 아닌 필드만 업데이트
    update_data = {k: v for k, v in task_update.model_dump().items() if v is not None}

    if update_data:
        tasks_collection.update_one({"id": task_id, "workspace_id": workspace_id}, {"$set": update_data})
    
    updated = tasks_collection.find_one({"id": task_id, "workspace_id": workspace_id})
    return {
        "workspace_id": updated.get("workspace_id"),
        "id": updated.get("id"),
        "title": updated.get("title"),
        "description": updated.get("description"),
        "priority": updated.get("priority", "medium"),
        "status": updated.get("status", "todo"),
        "category": updated.get("category", "general"),
        "tags": updated.get("tags", []),
        "embedding": updated.get("embedding", []),
        "due_date": updated.get("due_date"),
    }


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
):
    """
    태스크를 삭제합니다.
    
    Args:
        task_id: 삭제할 태스크의 ID
        x_workspace_id: 워크스페이스 고유 식별자 (헤더)
        
    Returns:
        dict: 삭제 결과 메시지
        
    Raises:
        HTTPException: 태스크가 존재하지 않을 때 (404)
    """
    workspace_id = x_workspace_id
    
    result = tasks_collection.delete_one({"id": task_id, "workspace_id": workspace_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다")
    return {"message": "태스크가 삭제되었습니다", "id": task_id}


@router.delete("/{task_id}/cascade")
def delete_task_cascade(
    task_id: str,
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
):
    """
    태스크와 연결된 엣지를 함께 삭제합니다.
    
    Args:
        task_id: 삭제할 태스크의 ID
        x_workspace_id: 워크스페이스 고유 식별자 (헤더)
        
    Returns:
        dict: 삭제 결과 (삭제된 태스크, 엣지 수)
        
    Raises:
        HTTPException: 태스크가 존재하지 않을 때 (404)
    """
    workspace_id = x_workspace_id
    
    # 태스크 존재 확인
    task = tasks_collection.find_one({"id": task_id, "workspace_id": workspace_id})
    if not task:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다")
    
    # 연결된 엣지 삭제 (같은 워크스페이스 내에서 source 또는 target이 해당 태스크인 경우)
    edge_result = edges_collection.delete_many({
        "workspace_id": workspace_id,
        "$or": [
            {"source": task_id},
            {"target": task_id}
        ]
    })
    
    # 태스크 삭제
    tasks_collection.delete_one({"id": task_id, "workspace_id": workspace_id})
    
    return {
        "message": "태스크와 연결된 엣지가 삭제되었습니다",
        "task_id": task_id,
        "deleted_edges_count": edge_result.deleted_count
    }


@router.post("/sync", response_model=SyncResponse)
def sync_tasks(
    sync_request: SyncRequest,
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
):
    """
    오프라인에서 생성/수정/삭제된 데이터를 서버와 동기화합니다.
    
    동작 방식:
    1. 클라이언트가 로컬 변경사항(tasks, edges)을 전송
    2. 서버는 각 항목을 upsert (존재하면 업데이트, 없으면 생성)
    3. deleted=True인 항목은 서버에서 삭제
    4. 동기화 완료 후 서버의 최신 데이터를 반환
    
    Args:
        sync_request: 동기화할 데이터 (tasks, edges)
        x_workspace_id: 워크스페이스 고유 식별자 (헤더)
        
    Returns:
        SyncResponse: 동기화 결과 및 서버의 최신 데이터
    """
    workspace_id = x_workspace_id
    
    stats = {
        "tasks_created": 0,
        "tasks_updated": 0,
        "tasks_deleted": 0,
        "edges_created": 0,
        "edges_updated": 0,
        "edges_deleted": 0,
    }
    
    # ========================================
    # 1. 태스크 동기화
    # ========================================
    for task in sync_request.tasks:
        existing = tasks_collection.find_one({
            "id": task.id, 
            "workspace_id": workspace_id
        })
        
        if task.deleted:
            # 삭제 요청
            if existing:
                # 연결된 엣지도 함께 삭제
                edges_collection.delete_many({
                    "workspace_id": workspace_id,
                    "$or": [
                        {"source": task.id},
                        {"target": task.id}
                    ]
                })
                tasks_collection.delete_one({
                    "id": task.id, 
                    "workspace_id": workspace_id
                })
                stats["tasks_deleted"] += 1
        elif existing:
            # 업데이트 (서버 데이터가 더 최신이면 스킵)
            server_updated_at = existing.get("updated_at")
            client_updated_at = task.updated_at
            
            # 클라이언트 데이터가 더 최신이거나 서버에 updated_at이 없으면 업데이트
            should_update = (
                server_updated_at is None or 
                client_updated_at is None or
                client_updated_at >= server_updated_at
            )
            
            if should_update:
                task_dict = task.model_dump(exclude={"deleted"})
                task_dict["workspace_id"] = workspace_id
                task_dict["updated_at"] = datetime.utcnow()
                
                # 임베딩 재생성
                text_for_embedding = f"{task.title} {task.description or ''} {' '.join(task.tags)}"
                from main import get_embedding
                task_dict["embedding"] = get_embedding(text_for_embedding)
                
                tasks_collection.update_one(
                    {"id": task.id, "workspace_id": workspace_id},
                    {"$set": task_dict}
                )
                stats["tasks_updated"] += 1
        else:
            # 새로 생성
            task_dict = task.model_dump(exclude={"deleted"})
            task_dict["workspace_id"] = workspace_id
            task_dict["updated_at"] = datetime.utcnow()
            
            # 임베딩 생성
            text_for_embedding = f"{task.title} {task.description or ''} {' '.join(task.tags)}"
            from main import get_embedding
            task_dict["embedding"] = get_embedding(text_for_embedding)
            
            tasks_collection.insert_one(task_dict)
            stats["tasks_created"] += 1
            
            # 태그 기반 엣지 자동 연결
            if task.tags:
                existing_tasks = tasks_collection.find({
                    "workspace_id": workspace_id,
                    "id": {"$ne": task.id},
                    "tags": {"$in": task.tags}
                })
                
                for existing_task in existing_tasks:
                    common_tags = set(task.tags) & set(existing_task.get("tags", []))
                    weight = len(common_tags) / max(len(task.tags), len(existing_task.get("tags", [])))
                    
                    edge_exists = edges_collection.find_one({
                        "workspace_id": workspace_id,
                        "$or": [
                            {"source": task.id, "target": existing_task["id"]},
                            {"source": existing_task["id"], "target": task.id}
                        ]
                    })
                    
                    if not edge_exists:
                        edges_collection.insert_one({
                            "workspace_id": workspace_id,
                            "source": task.id,
                            "target": existing_task["id"],
                            "weight": round(weight, 2)
                        })
    
    # ========================================
    # 2. 엣지 동기화
    # ========================================
    for edge in sync_request.edges:
        existing = edges_collection.find_one({
            "workspace_id": workspace_id,
            "$or": [
                {"source": edge.source, "target": edge.target},
                {"source": edge.target, "target": edge.source}
            ]
        })
        
        if edge.deleted:
            if existing:
                edges_collection.delete_one({"_id": existing["_id"]})
                stats["edges_deleted"] += 1
        elif existing:
            edges_collection.update_one(
                {"_id": existing["_id"]},
                {"$set": {"weight": edge.weight}}
            )
            stats["edges_updated"] += 1
        else:
            # source와 target 태스크가 존재하는지 확인
            source_exists = tasks_collection.find_one({
                "id": edge.source, 
                "workspace_id": workspace_id
            })
            target_exists = tasks_collection.find_one({
                "id": edge.target, 
                "workspace_id": workspace_id
            })
            
            if source_exists and target_exists:
                edges_collection.insert_one({
                    "workspace_id": workspace_id,
                    "source": edge.source,
                    "target": edge.target,
                    "weight": edge.weight
                })
                stats["edges_created"] += 1
    
    # ========================================
    # 3. 서버의 최신 데이터 반환
    # ========================================
    # 현재 워크스페이스의 모든 태스크
    all_tasks = list(tasks_collection.find({"workspace_id": workspace_id}))
    tasks_response = []
    for task in all_tasks:
        tasks_response.append({
            "workspace_id": task.get("workspace_id"),
            "id": task.get("id"),
            "title": task.get("title"),
            "description": task.get("description"),
            "priority": task.get("priority", "medium"),
            "status": task.get("status", "todo"),
            "category": task.get("category", "general"),
            "tags": task.get("tags", []),
            "embedding": task.get("embedding", []),
            "due_date": task.get("due_date"),
        })
    
    # 현재 워크스페이스의 모든 엣지
    all_edges = list(edges_collection.find({"workspace_id": workspace_id}))
    edges_response = []
    for edge in all_edges:
        edges_response.append({
            "workspace_id": edge.get("workspace_id"),
            "source": edge.get("source"),
            "target": edge.get("target"),
            "weight": edge.get("weight", 0.5),
        })
    
    return SyncResponse(
        tasks=tasks_response,
        edges=edges_response,
        sync_stats=stats,
        synced_at=datetime.utcnow()
    )
