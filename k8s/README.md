# Linkdo Backend - Kubernetes 배포 가이드

## 📋 사전 요구사항

### 1. Docker Desktop + Kubernetes 활성화
1. Docker Desktop 실행
2. Settings → Kubernetes 탭
3. "Enable Kubernetes" 체크 ✅
4. Apply & Restart

### 2. kubectl 설치 확인
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

## 🔧 유용한 명령어

```powershell
# Pod 상세 정보
kubectl describe pod <pod-name> -n linkdo

# Pod에 접속 (디버깅)
kubectl exec -it <pod-name> -n linkdo -- /bin/bash

# 로그 실시간 확인
kubectl logs -f <pod-name> -n linkdo

# 리소스 삭제
kubectl delete -f k8s/ --all

# 전체 네임스페이스 삭제 (모든 리소스 포함)
kubectl delete namespace linkdo
```

## 📊 스케일링

```powershell
# API Pod 개수 조정 (3개로)
kubectl scale deployment linkdo-api --replicas=3 -n linkdo
```

## ⚠️ 주의사항

1. `secrets.yaml`은 Git에 커밋하지 마세요! (`.gitignore`에 추가 권장)
2. 로컬 개발 시 `imagePullPolicy: Never` 사용
3. 프로덕션 배포 시 이미지를 Docker Registry에 푸시 필요



