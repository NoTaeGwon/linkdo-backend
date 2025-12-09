"""
================================================================
파일명       : routes/tasks.py
목적         : Tasks API 라우터
설명         :
    GET    /api/tasks       - 전체 태스크 조회
    GET    /api/tasks/{id}  - 특정 태스크 조회
    POST   /api/tasks       - 새 태스크 생성
    PUT    /api/tasks/{id}  - 태스크 수정
    DELETE /api/tasks/{id}  - 태스크 삭제
================================================================
"""

from fastapi import APIRouter, HTTPException
from typing import List
from models import TaskCreate, TaskUpdate, TaskResponse

# 라우터 생성
router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# MongoDB 컬렉션
tasks_collection = None


def set_collection(collection):
    """
    MongoDB 컬렉션을 주입받는 함수.
    
    Args:
        collection: MongoDB tasks 컬렉션 객체
    """
    global tasks_collection
    tasks_collection = collection


@router.get("/", response_model=List[TaskResponse])
def get_all_tasks():
    """
    전체 태스크 목록을 조회합니다.
    
    Returns:
        List[TaskResponse]: 모든 태스크 목록
    """
    tasks = list(tasks_collection.find())
    result = []
    for task in tasks:
        task_dict = {
            "id": task.get("id"),
            "title": task.get("title"),
            "description": task.get("description"),
            "priority": task.get("priority", "medium"),
            "status": task.get("status", "todo"),
            "category": task.get("category", "general"),
        }
        result.append(task_dict)
    return result


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    """
    특정 태스크를 조회합니다.
    
    Args:
        task_id: 조회할 태스크의 ID
        
    Returns:
        TaskResponse: 태스크 정보
        
    Raises:
        HTTPException: 태스크가 존재하지 않을 때 (404)
    """
    task = tasks_collection.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다")
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "description": task.get("description"),
        "priority": task.get("priority", "medium"),
        "status": task.get("status", "todo"),
        "category": task.get("category", "general"),
    }


@router.post("/", response_model=TaskResponse)
def create_task(task: TaskCreate):
    """
    새 태스크를 생성합니다.
    
    Args:
        task: 생성할 태스크 정보
        
    Returns:
        TaskResponse: 생성된 태스크 정보
        
    Raises:
        HTTPException: 이미 존재하는 ID일 때 (400)
    """
    if tasks_collection.find_one({"id": task.id}):
        raise HTTPException(status_code=400, detail="이미 존재하는 ID입니다")
    
    task_dict = task.model_dump()
    tasks_collection.insert_one(task_dict)
    return task_dict


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: str, task_update: TaskUpdate):
    """
    태스크를 수정합니다.
    
    Args:
        task_id: 수정할 태스크의 ID
        task_update: 수정할 필드들
        
    Returns:
        TaskResponse: 수정된 태스크 정보
        
    Raises:
        HTTPException: 태스크가 존재하지 않을 때 (404)
    """
    existing = tasks_collection.find_one({"id": task_id})
    if not existing:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다")
    
    # None이 아닌 필드만 업데이트
    update_data = {k: v for k, v in task_update.model_dump().items() if v is not None}
    
    if update_data:
        tasks_collection.update_one({"id": task_id}, {"$set": update_data})
    
    updated = tasks_collection.find_one({"id": task_id})
    return {
        "id": updated.get("id"),
        "title": updated.get("title"),
        "description": updated.get("description"),
        "priority": updated.get("priority", "medium"),
        "status": updated.get("status", "todo"),
        "category": updated.get("category", "general"),
    }


@router.delete("/{task_id}")
def delete_task(task_id: str):
    """
    태스크를 삭제합니다.
    
    Args:
        task_id: 삭제할 태스크의 ID
        
    Returns:
        dict: 삭제 결과 메시지
        
    Raises:
        HTTPException: 태스크가 존재하지 않을 때 (404)
    """
    result = tasks_collection.delete_one({"id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다")
    return {"message": "태스크가 삭제되었습니다", "id": task_id}
