# Linkdo Backend - Kubernetes 배포 가이드

이 문서는 **로컬 개발 환경**과 **EC2 프로덕션 환경** 모두에 대한 Kubernetes 배포 방법을 설명합니다.

---

## 📁 파일 구조

```
k8s/
├── namespace.yaml      # linkdo 네임스페이스 정의
├── secrets.yaml        # API 키 등 민감한 정보 (Git 제외)
├── mongo-deployment.yaml   # MongoDB Deployment + Service + PVC
├── api-deployment.yaml     # API Deployment + Service (NodePort)
├── ingress.yaml            # 로컬용 Ingress (api.linkdo.local)
└── ingress-prod.yaml       # 프로덕션용 Ingress (api.linkdo.cloud + TLS)
```

---

# 🖥️ 로컬 개발 환경 (Docker Desktop / minikube)

## 📋 사전 요구사항

### Docker Desktop + Kubernetes 활성화

1. Docker Desktop 실행
2. Settings → Kubernetes 탭
3. "Enable Kubernetes" 체크 ✅
4. Apply & Restart

### kubectl 설치 확인

```powershell
kubectl version --client
```

## 🚀 배포 순서

### Step 1: Docker 이미지 빌드

```powershell
# 프로젝트 루트에서 실행
docker build -t linkdo-backend:latest .
```

### Step 2: Secret 설정 (API 키)

```powershell
# GEMINI_API_KEY를 base64로 인코딩
$apiKey = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your-actual-gemini-api-key"))
echo $apiKey
# 출력된 값을 k8s/secrets.yaml의 GEMINI_API_KEY에 입력
```

### Step 3: 쿠버네티스 리소스 배포

```powershell
# 네임스페이스 생성
kubectl apply -f k8s/namespace.yaml

# Secret 배포
kubectl apply -f k8s/secrets.yaml

# MongoDB 배포
kubectl apply -f k8s/mongo-deployment.yaml

# API 서버 배포
kubectl apply -f k8s/api-deployment.yaml
```

### Step 4: 배포 확인

```powershell
# 모든 리소스 확인
kubectl get all -n linkdo

# Pod 상태 확인
kubectl get pods -n linkdo

# 로그 확인
kubectl logs -f deployment/linkdo-api -n linkdo
```

## 🌐 접속 방법

배포 완료 후 다음 주소로 접속:

- **API**: http://localhost:30080
- **Swagger UI**: http://localhost:30080/docs

---

# ☁️ EC2 프로덕션 환경 (k3s)

## 📋 사전 요구사항

- AWS EC2 인스턴스 (Ubuntu, t3.small 이상 권장)
- 도메인 연결 (api.linkdo.cloud → EC2 Public IP)
- 보안 그룹: 22(SSH), 80(HTTP), 443(HTTPS) 포트 오픈

## 🛠️ 초기 설정 (최초 1회)

### 1. k3s 설치 (Traefik 비활성화)

```bash
# k3s 설치 (내장 Traefik 비활성화)
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -

# kubectl 설정
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
```

### 2. Docker 설치

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 재로그인 필요
```

### 3. Nginx Ingress Controller 설치

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
```

### 4. cert-manager 설치 (Let's Encrypt 자동 인증서)

```bash
# cert-manager 설치
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.yaml

# 설치 완료 대기 (1-2분)
kubectl wait --for=condition=Ready pods --all -n cert-manager --timeout=120s
```

### 5. ClusterIssuer 생성 (Let's Encrypt)

```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## 🚀 배포 순서

### Step 1: 프로젝트 클론 및 이미지 빌드

```bash
git clone https://github.com/NoTaeGwon/linkdo-backend.git
cd linkdo-backend
docker build -t linkdo-backend:latest .
```

### Step 2: k3s에 이미지 로드

```bash
docker save linkdo-backend:latest -o /tmp/linkdo-backend.tar
sudo k3s ctr images import /tmp/linkdo-backend.tar
```

### Step 3: Secret 설정

```bash
# secrets.yaml 편집 (base64 인코딩된 API 키 입력)
nano k8s/secrets.yaml
```

### Step 4: 리소스 배포

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/mongo-deployment.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/ingress-prod.yaml
```

### Step 5: 배포 확인

```bash
# 전체 리소스 확인
kubectl get all -n linkdo

# Ingress 확인 (ADDRESS가 할당되었는지)
kubectl get ingress -n linkdo

# 인증서 상태 확인
kubectl get certificate -n linkdo
```

## 🔄 업데이트 배포

코드 변경 후 재배포:

```bash
cd ~/linkdo-backend
git pull origin main

# 이미지 재빌드 및 로드
docker build -t linkdo-backend:latest .
sudo k3s ctr images rm docker.io/library/linkdo-backend:latest 2>/dev/null || true
docker save linkdo-backend:latest -o /tmp/linkdo-backend.tar
sudo k3s ctr images import /tmp/linkdo-backend.tar

# Pod 재시작
kubectl rollout restart deployment/linkdo-api -n linkdo
```

## 🌐 접속 방법

- **API**: https://api.linkdo.cloud
- **Swagger UI**: https://api.linkdo.cloud/docs

---

# 🔧 공통 유용한 명령어

```bash
# Pod 상세 정보
kubectl describe pod <pod-name> -n linkdo

# Pod에 접속 (디버깅)
kubectl exec -it <pod-name> -n linkdo -- /bin/bash

# 로그 실시간 확인
kubectl logs -f <pod-name> -n linkdo

# Nginx Ingress 로그 확인
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=50

# 리소스 삭제
kubectl delete -f k8s/ --all

# 전체 네임스페이스 삭제 (모든 리소스 포함)
kubectl delete namespace linkdo
```

## 📊 스케일링

```bash
# API Pod 개수 조정 (3개로)
kubectl scale deployment linkdo-api --replicas=3 -n linkdo
```

## ⚠️ 주의사항

1. `secrets.yaml`은 Git에 커밋하지 마세요! (`.gitignore`에 추가됨)
2. `imagePullPolicy: Never` → 로컬 빌드 이미지 사용 (Registry 불필요)
3. EC2 보안 그룹에서 80, 443 포트가 열려있는지 확인
