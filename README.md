# Hit ArchLens

멀티 클라우드 아키텍처 다이어그램 자동 분석을 위한 통합 프레임워크입니다. Computer Vision과 Large Language Model을 결합하여 클라우드 서비스 아이콘을 자동으로 인식하고 분류합니다.

## 🎯 주요 기능

- **Computer Vision 기반 분석**: CLIP 모델을 사용한 이미지 유사도 검색
- **LLM 기반 분석**: GPT-4 Vision을 활용한 텍스트 기반 분석
- **하이브리드 분석**: CV와 LLM 결과를 융합한 고정확도 분석
- **AWS 데이터 수집**: 아이콘, 서비스 정보, 제품 정보 자동 수집
- **실시간 모니터링**: 데이터 수집 및 분석 과정 실시간 추적
- **성능 시각화**: 분석 결과 및 통계 데이터 시각화

## 🏗️ 아키텍처

```bash
Hit ArchLens/
├── core/                     # 핵심 프레임워크
│   ├── auto_labeler/        # 오토라벨링 추상 클래스
│   ├── data_collectors/     # 데이터 수집 프레임워크
│   ├── models.py           # 통합 데이터 모델
│   ├── taxonomy/           # 서비스 분류 시스템
│   └── utils/              # 유틸리티 함수
├── core/providers/aws/     # AWS 전용 구현체
│   ├── cv/                 # CV 기반 오토라벨러
│   ├── llm/                # LLM 기반 오토라벨러
│   └── hybrid/             # 하이브리드 오토라벨러
├── tools/                  # CLI 도구
├── configs/                # 설정 파일
├── out/                    # 모든 결과물 저장소
└── images/                 # 테스트 이미지
```

```bash
out/
├── aws/                      # AWS 데이터 수집 결과
│   ├── icons/               # 아이콘 매핑 파일
│   ├── services/            # 서비스 정보
│   ├── products/            # 제품 정보
│   └── taxonomy/            # 분류 정보
├── experiments/             # 실험 결과
│   ├── cv_results/          # CV 분석 결과
│   ├── llm_results/         # LLM 분석 결과
│   ├── hybrid_results/      # 하이브리드 분석 결과
│   └── batch_results/       # 배치 분석 결과
├── visualizations/          # 시각화 결과
│   ├── charts/              # 차트 및 그래프
│   ├── reports/             # 분석 리포트
│   └── dashboards/          # 대시보드
├── evaluation/              # 성능 평가
│   ├── metrics/             # 평가 지표
│   ├── comparisons/         # 방법론 비교
│   └── benchmarks/          # 벤치마크 결과
└── statistics/              # 통계 데이터
    ├── collection_stats/    # 수집 통계
    ├── analysis_stats/      # 분석 통계
    └── performance_stats/   # 성능 통계
```

## ⚙️ 설정

### 기본 설정 파일: `configs/default.yaml`

```yaml
# 데이터 설정
data:
  icons_dir: "out/aws/icons"
  taxonomy_csv: "out/aws_resources_models.csv"
  output_dir: "out"

# CV 설정
cv:
  clip_name: "ViT-B-32"
  clip_pretrained: "laion2b_s34b_b79k"
  device: "auto"

# LLM 설정
llm:
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"
  vision_model: "gpt-4-vision-preview"

# 분석 설정
detection:
  max_size: 1600
  min_area: 900
  max_area: 90000

# 성능 설정
performance:
  parallel_processing: true
  max_workers: 4
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd hit_archlens

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는 venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 2. AWS 아이콘 다운로드

```bash
# AWS 공식 아키텍처 아이콘 다운로드
wget https://d1.awsstatic.com/webteam/architecture-icons/q1-2024/Asset-Package_01242024.7c4f8b8b.zip -O Asset-Package.zip

# 또는 AWS 공식 사이트에서 수동 다운로드:
# https://aws.amazon.com/ko/architecture/icons/
```

### 3. 데이터 수집

```bash
# 모든 AWS 데이터 수집 (아이콘, 서비스, 제품 정보)
python tools/cli.py collect-data --data-type all --monitor --verbose

# 특정 데이터만 수집
python tools/cli.py collect-data --data-type icons --verbose
python tools/cli.py collect-data --data-type services --verbose
python tools/cli.py collect-data --data-type products --verbose
```

### 4. 오토라벨링 분석

```bash
# CV 기반 분석 (API 키 불필요)
python tools/cli.py analyze --input images/test_diagram.png --method cv --output out/experiments/cv_results --verbose

# LLM 기반 분석 (OpenAI API 키 필요)
export OPENAI_API_KEY="your-api-key-here"
python tools/cli.py analyze --input images/test_diagram.png --method llm --output out/experiments/llm_results --verbose

# 하이브리드 분석 (CV + LLM 결합)
python tools/cli.py analyze --input images/test_diagram.png --method hybrid --output out/experiments/hybrid_results --verbose
```

### 5. 배치 분석

```bash
# 여러 이미지 동시 분석
python tools/cli.py analyze --input images/ --method hybrid --output out/experiments/batch_results --verbose
```

### 6. 결과 시각화

```bash
# 분석 결과 시각화
python tools/cli.py visualize --input out/experiments/hybrid_results --output out/visualizations --verbose
```

## 📊 순차적 사용 가이드

### Phase 1: 초기 설정 및 데이터 수집

```bash
# 1. 환경 설정
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. AWS 아이콘 다운로드
wget https://d1.awsstatic.com/webteam/architecture-icons/q1-2024/Asset-Package_01242024.7c4f8b8b.zip -O Asset-Package.zip

# 3. 데이터 수집 (실시간 모니터링 포함)
python tools/cli.py collect-data --data-type all --monitor --verbose
```

**예상 시간**: 5-10분 (네트워크 속도에 따라 다름)

### Phase 2: CV 기반 분석 테스트

```bash
# 1. 테스트 이미지 준비
mkdir -p images
# AWS 아키텍처 다이어그램을 images/ 디렉터리에 복사

# 2. CV 기반 분석 실행
python tools/cli.py analyze --input images/test_diagram.png --method cv --output out/experiments/cv_results --verbose

# 3. 결과 확인
ls -la out/experiments/cv_results/
cat out/experiments/cv_results/analysis_results.json
```

**예상 시간**: 2-5분 (첫 실행 시 모델 다운로드 포함)

### Phase 3: LLM 기반 분석 (선택사항)

```bash
# 1. OpenAI API 키 설정
export OPENAI_API_KEY="your-api-key-here"

# 2. LLM 기반 분석 실행
python tools/cli.py analyze --input images/test_diagram.png --method llm --output out/experiments/llm_results --verbose

# 3. 결과 확인
ls -la out/experiments/llm_results/
cat out/experiments/llm_results/analysis_results.json
```

**예상 시간**: 1-3분 (API 응답 시간에 따라 다름)

### Phase 4: 하이브리드 분석

```bash
# 1. 하이브리드 분석 실행 (CV + LLM 결합)
python tools/cli.py analyze --input images/test_diagram.png --method hybrid --output out/experiments/hybrid_results --verbose

# 2. 결과 비교
ls -la out/experiments/
```

**예상 시간**: 3-8분 (CV + LLM 처리 시간)

### Phase 5: 성능 평가 및 시각화

```bash
# 1. 분석 결과 시각화
python tools/cli.py visualize --input out/experiments/hybrid_results --output out/visualizations --verbose

# 2. 성능 통계 확인
python tools/cli.py status --method hybrid --verbose

# 3. 결과 파일 확인
tree out/ -L 3
```

## 📁 출력 구조

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🔗 관련 링크

- [AWS 공식 아이콘](https://aws.amazon.com/ko/architecture/icons/)
- [OpenAI API 문서](https://platform.openai.com/docs/)
- [CLIP 모델](https://github.com/openai/CLIP)
- [OpenCLIP](https://github.com/mlfoundations/open_clip)

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해 주세요.

---

**Hit ArchLens** - 멀티 클라우드 아키텍처 분석의 새로운 표준

