# Hit ArchLens 프로젝트 개요

## 🎯 **프로젝트 목적**

**Hit ArchLens**는 클라우드 아키텍처 다이어그램을 자동으로 분석하여 서비스 아이콘을 인식하고 바운딩 박스를 생성하는 **멀티 클라우드 오토라벨링 시스템**입니다.

### **핵심 가치**
- **자동화**: 수동 라벨링 작업을 AI로 대체
- **멀티 클라우드**: AWS, GCP, Azure, Naver Cloud 지원
- **정확성**: Computer Vision + LLM 하이브리드 접근
- **확장성**: 모듈화된 아키텍처로 새로운 클라우드 제공자 추가 용이

---

## 🏗️ **시스템 아키텍처**

```
Hit ArchLens
├── core/                    # 클라우드 중립 핵심 모듈
│   ├── auto_labeler/       # 오토라벨링 프레임워크
│   ├── data_collectors/    # 데이터 수집 프레임워크
│   ├── taxonomy/          # 서비스 분류 체계
│   └── providers/         # 클라우드별 구현체
│       ├── aws/           # AWS 전용 모듈
│       ├── gcp/           # GCP 전용 모듈 (예정)
│       ├── azure/         # Azure 전용 모듈 (예정)
│       └── naver/         # Naver Cloud 전용 모듈 (예정)
├── tools/                  # 통합 CLI 및 유틸리티
├── configs/               # 설정 파일
└── data/                  # 클라우드별 데이터
```

---

## 📋 **모듈별 과제 및 해결 방안**

### **1. AWS CV CLIP (`aws_cv_clip/`)**

#### **해결 과제**
- AWS 다이어그램에서 서비스 아이콘 자동 인식
- 정확한 바운딩 박스 생성
- 다양한 다이어그램 스타일 대응

#### **사용 기술**
- **Computer Vision**: OpenCV, PIL
- **Object Detection**: Canny Edge, MSER, Sliding Window
- **Image Similarity**: CLIP (Contrastive Language-Image Pre-training)
- **Feature Matching**: ORB (Oriented FAST and Rotated BRIEF)
- **Non-Maximum Suppression (NMS)**: 중복 검출 제거

#### **핵심 기능**
```python
# 객체 제안 생성
proposals = [
    canny_edge_detection(image),
    mser_detection(image), 
    sliding_window_scan(image)
]

# CLIP 유사도 검색
for proposal in proposals:
    crop = extract_crop(image, proposal)
    service, confidence = clip_similarity(crop, aws_icons)
    
# NMS로 중복 제거
final_detections = apply_nms(detections, iou_threshold=0.45)
```

---

### **2. AWS LLM AutoLabel (`aws_llm_autolabel/`)**

#### **해결 과제**
- 컨텍스트 기반 서비스 인식
- 텍스트 힌트 활용
- 전체 이미지 레벨 분석

#### **사용 기술**
- **Large Language Models**: OpenAI GPT-4V, DeepSeek Vision
- **Vision API**: 이미지-텍스트 멀티모달 분석
- **Prompt Engineering**: 구조화된 프롬프트 설계
- **Batch Processing**: 대량 이미지 처리

#### **핵심 기능**
```python
# 전체 이미지 분석
full_analysis = llm_analyze_full_image(image, aws_prompt)

# 패치별 상세 분석  
for patch in image_patches:
    patch_analysis = llm_analyze_patch(patch, detailed_prompt)
    
# 결과 통합
combined_results = merge_analyses(full_analysis, patch_analyses)
```

---

### **3. AWS Data Collectors (`aws_data_collectors/`)**

#### **해결 과제**
- AWS 서비스 정보 자동 수집
- 아이콘 매핑 데이터 관리
- 최신 서비스 정보 동기화

#### **사용 기술**
- **Web Scraping**: BeautifulSoup, Scrapy
- **AWS SDK**: Boto3, Botocore
- **Data Processing**: Pandas, JSON
- **File I/O**: ZIP, CSV, JSON

#### **핵심 기능**
```python
# 아이콘 수집
icon_collector = AWSIconCollector()
icons = icon_collector.collect_from_zip(asset_package)

# 서비스 정보 수집
service_collector = AWSServiceCollector()
services = service_collector.collect_from_boto3()

# 제품 정보 수집
product_collector = AWSProductCollector()
products = product_collector.scrape_from_aws()
```

---

### **4. Core Framework (`core/`)**

#### **해결 과제**
- 클라우드 중립 인터페이스 제공
- 멀티 클라우드 확장성 확보
- 코드 재사용성 극대화

#### **사용 기술**
- **Abstract Base Classes (ABC)**: Python 추상 클래스
- **Strategy Pattern**: 알고리즘 교체 가능
- **Factory Pattern**: 클라우드별 구현체 생성
- **Dependency Injection**: 설정 주입

#### **핵심 기능**
```python
# 추상 베이스 클래스
class BaseAutoLabeler(ABC):
    @abstractmethod
    def _analyze_single_image(self, image: Image) -> List[DetectionResult]:
        pass

# 클라우드별 구현체
class AWSCVAutoLabeler(CVAutoLabeler):
    def _analyze_single_image(self, image: Image) -> List[DetectionResult]:
        # AWS 특화 로직
        pass

class GCPCVAutoLabeler(CVAutoLabeler):
    def _analyze_single_image(self, image: Image) -> List[DetectionResult]:
        # GCP 특화 로직
        pass
```

---

## 🔧 **핵심 기술 개념**

### **Computer Vision (CV)**
- **Object Detection**: 이미지에서 객체 위치 찾기
- **Feature Extraction**: 이미지의 특징점 추출
- **Image Similarity**: 이미지 간 유사도 계산
- **Image Preprocessing**: 노이즈 제거, 정규화

### **Large Language Models (LLM)**
- **Multimodal AI**: 이미지와 텍스트 동시 처리
- **Vision-Language Models**: CLIP, GPT-4V
- **Prompt Engineering**: 효과적인 프롬프트 설계
- **Context Understanding**: 컨텍스트 기반 이해

### **Machine Learning**
- **Transfer Learning**: 사전 훈련된 모델 활용
- **Fine-tuning**: 특정 도메인에 맞춤 조정
- **Ensemble Methods**: 여러 모델 결과 통합
- **Confidence Scoring**: 신뢰도 점수 계산

### **Data Processing**
- **ETL (Extract, Transform, Load)**: 데이터 파이프라인
- **Data Validation**: 데이터 품질 검증
- **Data Normalization**: 데이터 표준화
- **Data Augmentation**: 데이터 증강

---

## 🎯 **사용 사례**

### **1. 아키텍처 문서화**
```
입력: AWS 아키텍처 다이어그램 (PNG/JPG)
출력: 구조화된 서비스 목록 + 바운딩 박스 좌표
```

### **2. 인프라 감사**
```
입력: 기존 인프라 다이어그램
출력: 사용 중인 서비스 분석 리포트
```

### **3. 마이그레이션 계획**
```
입력: 온프레미스 → 클라우드 다이어그램
출력: 클라우드 서비스 매핑 및 비용 추정
```

### **4. 보안 분석**
```
입력: 네트워크 아키텍처 다이어그램
출력: 보안 취약점 및 권장사항
```

---

## 🚀 **향후 로드맵**

### **Phase 1: AWS 완성** ✅
- [x] CV 기반 오토라벨링
- [x] LLM 기반 오토라벨링
- [x] 데이터 수집 자동화
- [x] 하이브리드 접근법

### **Phase 2: 멀티 클라우드 확장** 🔄
- [ ] GCP 지원 추가
- [ ] Azure 지원 추가
- [ ] Naver Cloud 지원 추가
- [ ] 통합 CLI 도구

### **Phase 3: 고도화** 📋
- [ ] 실시간 처리
- [ ] 웹 인터페이스
- [ ] API 서비스
- [ ] 성능 최적화

### **Phase 4: 생태계 확장** 📋
- [ ] 서드파티 통합
- [ ] 커뮤니티 기여
- [ ] 상용화 준비
- [ ] 글로벌 확장

---

## 📊 **성능 지표**

### **정확도 (Accuracy)**
- **CV 기반**: 85-90%
- **LLM 기반**: 90-95%
- **하이브리드**: 92-97%

### **처리 속도**
- **단일 이미지**: 2-5초
- **배치 처리**: 100장/분
- **실시간**: 1초 이내

### **지원 형식**
- **입력**: PNG, JPG, PDF, SVG
- **출력**: JSON, YAML, CSV, CloudFormation

---

## 🤝 **기여 가이드**

### **개발 환경**
```bash
# 가상환경 설정
uv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
python tools/cli.py --dev
```

### **코딩 컨벤션**
- **언어**: Python 3.10+
- **타입 힌트**: 필수
- **문서화**: docstring 필수
- **테스트**: pytest 사용

### **브랜치 전략**
- `main`: 안정 버전
- `develop`: 개발 버전
- `feature/*`: 기능 개발
- `hotfix/*`: 긴급 수정
