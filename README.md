# 🔗 Linkdo Backend

> **AI 기반 태스크 그래프 관리 시스템의 백엔드 API**

태스크를 노드로, 연관성을 엣지로 표현하여 **그래프 형태로 시각화**하는 태스크 관리 앱의 백엔드입니다.  
Google Gemini API를 활용한 **텍스트 임베딩**과 **PCA 차원 축소**를 통해 유사한 태스크를 자동으로 군집화합니다.

<br>

## 🌐 Live Demo

| 서비스 | URL |
|--------|-----|
| **프론트엔드** | https://linkdo.cloud |
| **백엔드 API** | https://api.linkdo.cloud |
| **API 문서** | https://api.linkdo.cloud/docs |

<br>

## ✨ 주요 기능

### AI 기반 태스크 배치
- **텍스트 임베딩**: Google Gemini API로 태스크의 제목, 설명, 태그를 벡터화
- **PCA 차원 축소**: 고차원 임베딩을 2D 좌표로 변환하여 시각화
- **자동 군집화**: 의미적으로 유사한 태스크들이 가까이 배치됨

### 자동 엣지 연결
- 태스크 생성 시 **공통 태그 기반**으로 기존 태스크와 자동 연결
- 엣지 가중치 = `공통 태그 수 / 최대 태그 수`

### AI 태그 추천
- Gemini LLM을 활용한 **맥락 기반 태그 제안**
- 기존 태그 목록을 참고하여 일관성 있는 태그 추천

### 그래프 자동 정렬
- 전체 태스크를 PCA로 재계산하여 **최적의 배치** 제공
- StandardScaler로 정규화하여 일관된 시각화

### Workspace 기반 데이터 분리
- 각 사용자/브라우저별 **독립적인 데이터 공간** 제공
- `X-Workspace-ID` 헤더로 데이터 격리

### 오프라인 동기화 (Sync API)
- **Offline-First** 지원: 오프라인에서 작업 후 온라인 시 자동 동기화
- Bulk upsert: 여러 태스크/엣지를 한 번에 동기화
- Soft delete: `deleted: true` 플래그로 삭제 동기화
- 충돌 해결: `updated_at` 타임스탬프 기반

<br>

## 🛠️ 기술 스택

| 영역 | 기술 |
|------|------|
| **Framework** | FastAPI (Python 3.11) |
| **Database** | MongoDB 7.0 |
| **AI/ML** | Google Gemini API (gemini-2.5-flash, gemini-embedding-001), scikit-learn (PCA) |
| **Container** | Docker, Docker Compose |
| **Orchestration** | Kubernetes (k3s) |
| **Ingress** | Traefik (k3s 내장) |
| **SSL** | Let's Encrypt (cert-manager) |
| **CI/CD** | GitHub Actions |
| **Cloud** | AWS EC2 |
| **Frontend Hosting** | Vercel |

<br>

## 🏗️ 시스템 아키텍처

<p align="center">
  <img src="docs/images/architecture.svg" alt="System Architecture" width="700"/>
</p>

<br>

## 📁 프로젝트 구조

```
linkdo-backend/
├── main.py              # FastAPI 앱 진입점, 설정
├── models.py            # Pydantic 데이터 모델
├── routes/
│   ├── tasks.py         # 태스크 CRUD API
│   ├── edges.py         # 엣지 CRUD API
│   ├── tags.py          # 태그 조회/추천 API
│   └── graph.py         # 그래프 데이터/자동정렬 API
├── k8s/                  # Kubernetes 매니페스트
│   ├── namespace.yaml
│   ├── secrets.yaml
│   ├── api-deployment.yaml
│   ├── mongo-deployment.yaml
│   └── ingress.yaml      # Traefik Ingress 설정
├── .github/
│   └── workflows/
│       └── ci.yml        # CI/CD 파이프라인
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

<br>

## 📡 API 엔드포인트

### 🔑 인증
모든 API 요청에 `X-Workspace-ID` 헤더가 **필수**입니다.

```bash
# 프로덕션
curl -H "X-Workspace-ID: your-workspace-id" https://api.linkdo.cloud/api/tasks/

# 로컬 개발
curl -H "X-Workspace-ID: your-workspace-id" http://localhost:8000/api/tasks/
```

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tasks/` | 전체 태스크 조회 |
| `GET` | `/api/tasks/{id}` | 특정 태스크 조회 |
| `POST` | `/api/tasks/` | 태스크 생성 (임베딩 + 자동 엣지 연결) |
| `POST` | `/api/tasks/sync` | **오프라인 동기화** (bulk upsert) |
| `PATCH` | `/api/tasks/{id}` | 태스크 부분 수정 |
| `DELETE` | `/api/tasks/{id}` | 태스크 삭제 |
| `DELETE` | `/api/tasks/{id}/cascade` | 태스크 + 연결된 엣지 삭제 |

### Edges
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/edges/` | 전체 엣지 조회 |
| `POST` | `/api/edges/` | 엣지 생성 |
| `DELETE` | `/api/edges/{id}` | 엣지 삭제 |

### Tags
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tags/` | 모든 태그 목록 |
| `POST` | `/api/tags/suggest-tags` | AI 태그 추천 |

### Graph
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/graph/` | 그래프 데이터 (tasks + edges + 좌표) |
| `POST` | `/api/graph/auto-arrange` | PCA 기반 자동 정렬 |

<br>

## 🚀 실행 방법

### 1. 로컬 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정 (.env)
MONGO_URI=mongodb://localhost:27017/linkdo
GEMINI_API_KEY=your_api_key

# 서버 실행
uvicorn main:app --reload --port 8000
```

### 2. Docker Compose

```bash
docker-compose up -d
```

### 3. Kubernetes (minikube) - 로컬

```bash
# minikube 시작
minikube start

# minikube Docker 환경 연결
minikube docker-env | Invoke-Expression  # PowerShell
# eval $(minikube docker-env)            # Linux/Mac

# Docker 이미지 빌드
docker build -t linkdo-backend:latest .

# 리소스 배포
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/mongo-deployment.yaml
kubectl apply -f k8s/api-deployment.yaml

# 포트포워딩 (localhost:8080으로 접근)
kubectl port-forward svc/linkdo-api 8080:80 -n linkdo
```

### 3-1. Ingress 설정 (도메인 기반 접근)

```bash
# NGINX Ingress Controller 활성화
minikube addons enable ingress

# Ingress 리소스 배포
kubectl apply -f k8s/ingress.yaml

# hosts 파일에 도메인 추가 (관리자 권한 필요)
# Windows: C:\Windows\System32\drivers\etc\hosts
# Linux/Mac: /etc/hosts
# 아래 내용 추가:
127.0.0.1 api.linkdo.local

# minikube tunnel 실행 (터미널 유지 필요)
minikube tunnel

# 이제 도메인으로 접근 가능
curl http://api.linkdo.local/api/tasks/ -H "X-Workspace-ID: test"
```

### 4. AWS EC2 + k3s (프로덕션)

```bash
# EC2 인스턴스에 SSH 접속
ssh -i "your-key.pem" ubuntu@your-ec2-ip

# k3s 설치 (경량 Kubernetes)
curl -sfL https://get.k3s.io | sh -

# kubectl 설정
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config

# Docker 설치
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 프로젝트 클론 및 빌드
git clone https://github.com/NoTaeGwon/linkdo-backend.git
cd linkdo-backend
docker build -t linkdo-backend:latest .

# k3s에 이미지 import
docker save linkdo-backend:latest -o /tmp/linkdo-backend.tar
sudo k3s ctr images import /tmp/linkdo-backend.tar

# 리소스 배포
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/mongo-deployment.yaml
kubectl apply -f k8s/api-deployment.yaml

# 상태 확인
kubectl get pods -n linkdo
```

<br>

## 🔄 CI/CD 파이프라인

GitHub Actions를 통해 **자동 테스트, 빌드, 배포**가 이루어집니다.

```
main 브랜치 Push
      ↓
  [test] Python 설정, 의존성 설치, Lint 검사
      ↓
  [build] Docker 이미지 빌드 테스트
      ↓
  [deploy] EC2에 SSH 접속 → git pull → docker build → k3s 배포
      ↓
  ✅ 자동 배포 완료
```

### 워크플로우 설정

`.github/workflows/ci.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: |
          pip install flake8
          flake8 . --count --select=E9,F63,F7,F82 --show-source

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t linkdo-backend:${{ github.sha }} .

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USERNAME }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd ~/linkdo-backend
            git pull origin main
            docker build -t linkdo-backend:latest .
            # 이미지 캐시 삭제 후 새로 import
            sudo k3s ctr images rm docker.io/library/linkdo-backend:latest 2>/dev/null || true
            docker save linkdo-backend:latest -o /tmp/linkdo-backend.tar
            sudo k3s ctr images import /tmp/linkdo-backend.tar
            # sudo 필수 (k3s kubeconfig 권한)
            sudo kubectl rollout restart deployment/linkdo-api -n linkdo
```

### GitHub Secrets 설정

| Secret | 설명 |
|--------|------|
| `EC2_HOST` | EC2 퍼블릭 IP 또는 Elastic IP |
| `EC2_USERNAME` | SSH 유저명 (ubuntu) |
| `EC2_SSH_KEY` | SSH 프라이빗 키 내용 |

<br>

## 🔧 핵심 알고리즘

### 텍스트 임베딩 → 2D 좌표 변환

> **gemini-embedding-001**: 3,072차원 벡터 → PCA → 2D 좌표

```python
# 1. Gemini API로 텍스트 임베딩 생성 (3,072차원)
text = f"{title} {description} {' '.join(tags)}"
embedding = gemini_client.models.embed_content(
    model="gemini-embedding-001",
    contents=text
)

# 2. PCA로 2D 차원 축소
pca = PCA(n_components=2)
coords_2d = pca.fit_transform(embeddings)

# 3. StandardScaler로 정규화 및 스케일링
scaler = StandardScaler()
coords_2d = scaler.fit_transform(coords_2d) * 40
```

### 자동 엣지 연결

```python
# 공통 태그가 있는 기존 태스크 검색
existing_tasks = tasks_collection.find({
    "id": {"$ne": new_task.id},
    "tags": {"$in": new_task.tags},
    "workspace_id": workspace_id  # 같은 workspace 내에서만
})

# 가중치 계산 및 엣지 생성
for task in existing_tasks:
    common_tags = set(new_task.tags) & set(task.tags)
    weight = len(common_tags) / max(len(new_task.tags), len(task.tags))
    edges_collection.insert_one({
        "source": new_task.id,
        "target": task.id,
        "weight": weight,
        "workspace_id": workspace_id
    })
```

<br>

## 📊 데이터 모델

### Task
```typescript
{
  id: string;            // 고유 식별자
  workspace_id: string;  // 워크스페이스 ID
  title: string;         // 제목
  description?: string;  // 설명
  priority: "low" | "medium" | "high" | "critical";
  status: "todo" | "in-progress" | "done";
  category: string;      // 카테고리
  tags: string[];        // 태그 배열
  embedding: number[];   // 임베딩 벡터
  due_date?: datetime;   // 마감일
}
```

### Edge
```typescript
{
  id: string;            // 고유 식별자
  workspace_id: string;  // 워크스페이스 ID
  source: string;        // 시작 태스크 ID
  target: string;        // 끝 태스크 ID
  weight: number;        // 연관도 (0~1)
}
```

<br>

## 🌐 배포 아키텍처 (AWS EC2 + k3s)

<p align="center">
  <img src="docs/images/aws-ec2-k3s-architecture.svg" alt="AWS EC2 + k3s Architecture" width="800"/>
</p>

### 인프라 구성

| 구성요소 | 설명 |
|----------|------|
| **EC2 (t3.small)** | 2 vCPU, 2GB RAM |
| **k3s** | 경량 Kubernetes (Rancher) |
| **Traefik** | Ingress Controller + 자동 HTTPS |
| **cert-manager** | Let's Encrypt 인증서 자동 발급/갱신 |
| **MongoDB** | PersistentVolume으로 데이터 영속성 보장 |
| **Vercel** | 프론트엔드 호스팅 (React) |
| **GitHub Actions** | CI/CD 자동 배포 |

### 주요 인프라 설정

#### HTTPS 리다이렉트 미들웨어
리버스 프록시(Traefik) 뒤에서 실행될 때 `X-Forwarded-Proto` 헤더를 확인하여 리다이렉트 URL의 스킴을 HTTPS로 유지합니다.

```python
# main.py - HTTPS 스킴 강제 미들웨어
@app.middleware("http")
async def force_https_scheme(request: Request, call_next):
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    response = await call_next(request)
    
    if response.status_code in (301, 302, 303, 307, 308):
        location = response.headers.get("location", "")
        if location.startswith("http://") and forwarded_proto == "https":
            response.headers["location"] = "https://" + location[7:]
    
    return response
```

#### iptables 설정 (EC2)
외부 트래픽만 Traefik으로 리다이렉트 (Pod 외부 통신 보장):

```bash
# 올바른 설정 - 외부 인터페이스(ens5)에서 들어오는 트래픽만 리다이렉트
sudo iptables -t nat -A PREROUTING -i ens5 -p tcp --dport 80 -j REDIRECT --to-port 30348
sudo iptables -t nat -A PREROUTING -i ens5 -p tcp --dport 443 -j REDIRECT --to-port 31374
```

<br>

## 📝 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `MONGO_URI` | MongoDB 연결 문자열 | `mongodb://localhost:27017/linkdo` |
| `GEMINI_API_KEY` | Google Gemini API 키 | - |

<br>

## 🔗 관련 저장소

| 저장소 | 설명 | URL |
|--------|------|-----|
| [linkdo-frontend](https://github.com/NoTaeGwon/linkdo-frontend) | React 기반 프론트엔드 | https://linkdo.cloud |

<br>

## 📄 라이선스

MIT License

<br>
