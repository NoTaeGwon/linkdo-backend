"""
================================================================
파일명       : routes/graph.py
목적         : Graph API 라우터
설명         :
    GET    /api/graph              - 그래프 데이터 조회 (tasks + edges + PCA 좌표)
    POST   /api/graph/auto-arrange - 전체 태스크 PCA 재정렬
================================================================
"""

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from fastapi import APIRouter, Header

router = APIRouter(prefix="/api/graph", tags=["graph"])

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


@router.get("/")
def get_graph(x_workspace_id: str = Header(..., alias="X-Workspace-ID")):
    """
    그래프 데이터 통합 (tasks + edges)
    PCA로 계산된 2D 좌표 포함

    Args:
        x_workspace_id: 워크스페이스 고유 식별자 (헤더)

    Returns:
        dict: { tasks: [...], edges: [...] }
    """
    workspace_id = x_workspace_id
    
    # Tasks 조회 (해당 워크스페이스만)
    tasks = list(tasks_collection.find({"workspace_id": workspace_id}))

    # 임베딩이 있는 테스크들로 PCA 계산
    embeddings = []
    tasks_with_embedding = []

    for task in tasks:
        embedding = task.get("embedding", [])
        if embedding:
            embeddings.append(embedding)
            tasks_with_embedding.append(task)
    
    # PCA로 2D 좌표 계산
    coordinates = {}
    if len(embeddings) >= 2:
        pca = PCA(n_components=2)
        coords_2d = pca.fit_transform(np.array(embeddings))

        # StandardScaler로 정규화 후 스케일링
        scaler = StandardScaler()
        coords_2d = scaler.fit_transform(coords_2d) * 40

        for i, task in enumerate(tasks_with_embedding):
            coordinates[task.get("id")] = {
                "x": float(coords_2d[i][0]),
                "y": float(coords_2d[i][1])
            }

    # Tasks 결과 생성
    tasks_result = []
    for task in tasks:
        task_id = task.get("id")
        coord = coordinates.get(task_id, {"x": 0, "y": 0})

        tasks_result.append({
            "id": task_id,
            "title": task.get("title"),
            "description": task.get("description"),
            "priority": task.get("priority", "medium"),
            "status": task.get("status", "todo"),
            "category": task.get("category", "general"),
            "tags": task.get("tags", []),
            "due_date": task.get("due_date"),
            "x": coord["x"],
            "y": coord["y"],
        })
    
    # Edges 조회 (해당 워크스페이스만)
    edges = list(edges_collection.find({"workspace_id": workspace_id}))
    edges_result = []
    for edge in edges:
        edges_result.append({
            "source": edge.get("source"),
            "target": edge.get("target"),
            "weight": edge.get("weight", 0.5),
        })

    return {"tasks": tasks_result, "edges": edges_result}


@router.post("/auto-arrange")
def auto_arrange(x_workspace_id: str = Header(..., alias="X-Workspace-ID")):
    """
    전체 태스크를 PCA로 재정렬하여 좌표 반환
    
    Args:
        x_workspace_id: 워크스페이스 고유 식별자 (헤더)

    Returns:
        dict: { positions: [{ id, x, y }, ...] }
    """
    workspace_id = x_workspace_id
    
    tasks = list(tasks_collection.find({"workspace_id": workspace_id}))
    
    embeddings = []
    tasks_with_embedding = []
    
    for task in tasks:
        embedding = task.get("embedding", [])
        if embedding:
            embeddings.append(embedding)
            tasks_with_embedding.append(task)
    
    positions = []
    
    if len(embeddings) >= 2:
        pca = PCA(n_components=2)
        coords_2d = pca.fit_transform(np.array(embeddings))
        
        # StandardScaler로 정규화 후 스케일링
        scaler = StandardScaler()
        coords_2d = scaler.fit_transform(coords_2d) * 40
        
        for i, task in enumerate(tasks_with_embedding):
            positions.append({
                "id": task.get("id"),
                "x": float(coords_2d[i][0]),
                "y": float(coords_2d[i][1])
            })
    else:
        # 임베딩 2개 미만이면 기본 좌표
        for i, task in enumerate(tasks_with_embedding):
            positions.append({
                "id": task.get("id"),
                "x": float(i * 100),
                "y": 0.0
            })
    
    # 임베딩 없는 태스크는 (0, 0)
    embedded_ids = {t.get("id") for t in tasks_with_embedding}
    for task in tasks:
        if task.get("id") not in embedded_ids:
            positions.append({
                "id": task.get("id"),
                "x": 0.0,
                "y": 0.0
            })
    
    return {"positions": positions}
