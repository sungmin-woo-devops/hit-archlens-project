# Hit ArchLens 기술 용어집

## 🔍 **Computer Vision (CV)**

### **Object Detection (객체 검출)**
- **정의**: 이미지에서 특정 객체의 위치와 종류를 찾는 기술
- **사용처**: AWS 아이콘 위치 검출
- **기법**: Canny Edge, MSER, Sliding Window

### **Bounding Box (바운딩 박스)**
- **정의**: 객체를 둘러싸는 직사각형 좌표 [x, y, width, height]
- **사용처**: 검출된 서비스 아이콘의 위치 표시
- **형식**: `[x1, y1, x2, y2]` 또는 `[x, y, width, height]`

### **Canny Edge Detection**
- **정의**: 이미지의 경계선을 검출하는 알고리즘
- **원리**: 노이즈 제거 → 그래디언트 계산 → 비최대 억제 → 이중 임계값
- **매개변수**: `low_threshold`, `high_threshold`

### **MSER (Maximally Stable Extremal Regions)**
- **정의**: 이미지에서 안정적인 극값 영역을 찾는 알고리즘
- **특징**: 크기 변화에 강함, 텍스트/로고 검출에 효과적
- **매개변수**: `delta`, `min_area`, `max_area`

### **Sliding Window**
- **정의**: 이미지를 일정 크기의 윈도우로 스캔하는 기법
- **목적**: 모든 가능한 위치에서 객체 검출
- **매개변수**: `window_size`, `stride`

### **Non-Maximum Suppression (NMS)**
- **정의**: 중복 검출을 제거하는 후처리 기법
- **원리**: IoU(Intersection over Union) 기반 중복 제거
- **임계값**: 보통 0.3-0.5 사용

---

## 🤖 **Large Language Models (LLM)**

### **Multimodal AI**
- **정의**: 텍스트, 이미지, 음성 등 여러 모달리티를 동시에 처리하는 AI
- **예시**: GPT-4V, CLIP, DeepSeek Vision
- **장점**: 컨텍스트 이해 능력 향상

### **Vision-Language Models**
- **정의**: 이미지와 텍스트를 연결하는 모델
- **대표 모델**: CLIP, GPT-4V, LLaVA
- **사용처**: 이미지 설명, 이미지 검색, 시각적 질의응답

### **Prompt Engineering**
- **정의**: AI 모델에 효과적인 지시를 주는 기술
- **요소**: 명확성, 구체성, 예시 포함
- **예시**: "AWS 아키텍처 다이어그램에서 서비스 아이콘을 찾아서 JSON 형식으로 출력하세요"

### **Context Window**
- **정의**: 모델이 한 번에 처리할 수 있는 텍스트 길이
- **제한**: 모델별로 다름 (GPT-4: 128K, Claude: 200K)
- **고려사항**: 긴 다이어그램 분석 시 청크 분할 필요

---

## 🎯 **Image Processing**

### **CLIP (Contrastive Language-Image Pre-training)**
- **정의**: OpenAI가 개발한 이미지-텍스트 연결 모델
- **원리**: 이미지와 텍스트를 같은 벡터 공간에 매핑
- **사용처**: 이미지 유사도 검색, 이미지 분류
- **장점**: 제로샷 학습 가능

### **ORB (Oriented FAST and Rotated BRIEF)**
- **정의**: 빠른 특징점 검출 및 매칭 알고리즘
- **구성**: FAST (특징점 검출) + BRIEF (특징점 기술)
- **사용처**: 이미지 정합, 객체 추적

### **Feature Matching**
- **정의**: 두 이미지 간의 특징점을 매칭하는 기술
- **알고리즘**: SIFT, SURF, ORB, FLANN
- **사용처**: 이미지 정합, 객체 인식

### **Image Similarity**
- **정의**: 두 이미지 간의 유사도를 계산하는 기술
- **방법**: 유클리드 거리, 코사인 유사도, 구조적 유사도
- **사용처**: 중복 이미지 검출, 유사 이미지 검색

---

## 📊 **Machine Learning**

### **Transfer Learning**
- **정의**: 사전 훈련된 모델을 새로운 작업에 적용하는 기법
- **장점**: 적은 데이터로도 높은 성능, 빠른 학습
- **예시**: ImageNet으로 훈련된 모델을 AWS 아이콘 인식에 적용

### **Fine-tuning**
- **정의**: 사전 훈련된 모델을 특정 도메인에 맞춤 조정
- **방법**: 마지막 레이어만 재훈련 또는 전체 모델 미세 조정
- **사용처**: AWS 아이콘 특화 모델 생성

### **Ensemble Methods**
- **정의**: 여러 모델의 결과를 결합하여 성능 향상
- **기법**: Voting, Averaging, Stacking
- **사용처**: CV + LLM 결과 통합

### **Confidence Scoring**
- **정의**: 모델 예측의 신뢰도를 점수화
- **범위**: 0.0 (불확실) ~ 1.0 (확실)
- **사용처**: 검출 결과 필터링, 후처리

---

## 🔄 **Data Processing**

### **ETL (Extract, Transform, Load)**
- **정의**: 데이터 추출, 변환, 적재 과정
- **단계**:
  1. **Extract**: 원본 데이터 수집
  2. **Transform**: 데이터 정제 및 변환
  3. **Load**: 목적지에 데이터 적재

### **Data Validation**
- **정의**: 데이터 품질 및 무결성 검증
- **검증 항목**: 형식, 범위, 중복, 누락
- **도구**: Pydantic, Great Expectations

### **Data Normalization**
- **정의**: 데이터를 표준 형식으로 변환
- **목적**: 일관성 확보, 비교 가능성
- **예시**: 서비스명 정규화 (EC2 → Amazon EC2)

### **Data Augmentation**
- **정의**: 기존 데이터를 변형하여 새로운 데이터 생성
- **기법**: 회전, 크기 조정, 노이즈 추가
- **목적**: 모델 일반화 성능 향상

---

## ☁️ **Cloud Computing**

### **Multi-Cloud**
- **정의**: 여러 클라우드 제공자를 동시에 사용하는 전략
- **장점**: 벤더 종속성 회피, 최적 비용, 고가용성
- **지원 대상**: AWS, GCP, Azure, Naver Cloud

### **Cloud-Native**
- **정의**: 클라우드 환경에 최적화된 애플리케이션 설계
- **특징**: 마이크로서비스, 컨테이너, 서버리스
- **장점**: 확장성, 유연성, 관리 효율성

### **Infrastructure as Code (IaC)**
- **정의**: 인프라를 코드로 정의하고 관리
- **도구**: Terraform, CloudFormation, Ansible
- **장점**: 버전 관리, 재현 가능성, 자동화

---

## 🏗️ **Software Architecture**

### **Abstract Base Classes (ABC)**
- **정의**: 추상 메서드를 포함한 기본 클래스
- **목적**: 인터페이스 정의, 다형성 구현
- **예시**: `BaseAutoLabeler`, `BaseDataCollector`

### **Strategy Pattern**
- **정의**: 알고리즘을 캡슐화하여 런타임에 교체 가능
- **사용처**: 클라우드별 오토라벨링 전략
- **장점**: 확장성, 유지보수성

### **Factory Pattern**
- **정의**: 객체 생성을 캡슐화하는 패턴
- **사용처**: 클라우드별 구현체 생성
- **장점**: 객체 생성 로직 분리

### **Dependency Injection**
- **정의**: 의존성을 외부에서 주입하는 패턴
- **목적**: 결합도 감소, 테스트 용이성
- **예시**: 설정 객체 주입

---

## 📈 **Performance Metrics**

### **Accuracy (정확도)**
- **정의**: 전체 예측 중 올바른 예측의 비율
- **계산**: `(TP + TN) / (TP + TN + FP + FN)`
- **목표**: 90% 이상

### **Precision (정밀도)**
- **정의**: 양성 예측 중 실제 양성의 비율
- **계산**: `TP / (TP + FP)`
- **의미**: 오탐지 방지

### **Recall (재현율)**
- **정의**: 실제 양성 중 올바르게 예측된 비율
- **계산**: `TP / (TP + FN)`
- **의미**: 누락 방지

### **F1-Score**
- **정의**: Precision과 Recall의 조화평균
- **계산**: `2 * (Precision * Recall) / (Precision + Recall)`
- **목표**: 0.9 이상

### **IoU (Intersection over Union)**
- **정의**: 예측 박스와 실제 박스의 겹침 정도
- **계산**: `Intersection Area / Union Area`
- **임계값**: 0.5 이상을 올바른 검출로 간주

---

## 🔧 **Development Tools**

### **Type Hints**
- **정의**: Python의 타입 정보 제공 기능
- **목적**: 코드 가독성, IDE 지원, 버그 방지
- **예시**: `def analyze_image(image: Image.Image) -> List[DetectionResult]:`

### **Dataclasses**
- **정의**: Python 3.7+의 데이터 클래스 데코레이터
- **목적**: 보일러플레이트 코드 감소
- **예시**: `@dataclass class DetectionResult:`

### **Virtual Environment**
- **정의**: 프로젝트별 독립적인 Python 환경
- **도구**: venv, virtualenv, uv
- **목적**: 의존성 충돌 방지

### **Package Management**
- **도구**: pip, uv, poetry
- **목적**: 의존성 관리, 패키지 설치
- **파일**: requirements.txt, pyproject.toml

---

## 📋 **File Formats**

### **JSON (JavaScript Object Notation)**
- **용도**: 데이터 교환, 설정 파일
- **특징**: 가독성, 언어 독립성
- **예시**: 검출 결과 저장

### **YAML (YAML Ain't Markup Language)**
- **용도**: 설정 파일, 데이터 직렬화
- **특징**: 가독성, 계층 구조
- **예시**: 프로젝트 설정

### **CSV (Comma-Separated Values)**
- **용도**: 표 형태 데이터 저장
- **특징**: 단순함, 스프레드시트 호환
- **예시**: 서비스 목록, 아이콘 매핑

### **ZIP**
- **용도**: 파일 압축, 아카이브
- **특징**: 크기 감소, 여러 파일 묶기
- **예시**: AWS 아이콘 패키지

---

## 🚀 **Deployment & Operations**

### **Containerization**
- **도구**: Docker, Podman
- **목적**: 환경 일관성, 배포 용이성
- **특징**: 격리, 이식성

### **CI/CD (Continuous Integration/Deployment)**
- **정의**: 지속적 통합 및 배포
- **도구**: GitHub Actions, GitLab CI, Jenkins
- **목적**: 자동화, 품질 보장

### **Monitoring**
- **도구**: Prometheus, Grafana, ELK Stack
- **목적**: 성능 추적, 문제 감지
- **지표**: 처리 시간, 정확도, 오류율

### **Logging**
- **도구**: Python logging, structlog
- **목적**: 디버깅, 감사, 모니터링
- **레벨**: DEBUG, INFO, WARNING, ERROR, CRITICAL
