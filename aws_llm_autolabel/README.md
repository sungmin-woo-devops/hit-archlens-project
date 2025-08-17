# AWS LLM 오토라벨러

LLM Vision API를 사용하여 AWS 다이어그램에서 서비스 아이콘을 인식하고 바운딩 박스를 생성하는 도구입니다.

## 🚀 주요 기능

- **LLM 기반 분석**: OpenAI GPT-4 Vision, DeepSeek Vision 등 지원
- **두 가지 분석 모드**:
  - `full_image_llm`: 전체 이미지를 한 번에 분석
  - `patch_llm`: 객체 제안 후 개별 패치 분석
- **다양한 출력 형식**: JSON, YOLO, COCO, Label Studio
- **택소노미 정규화**: AWS 서비스명 자동 정규화
- **배치 처리**: 여러 이미지 동시 처리
- **테스트 모드**: API 키 없이도 테스트 가능

## 📁 구조

```
aws_llm_autolabel/
├── src/
│   ├── llm_auto_labeler.py    # 메인 오토라벨러 클래스
│   ├── llm_providers.py       # LLM 제공자 추상화
│   ├── prompts.py             # 프롬프트 관리
│   ├── main.py                # CLI 실행 파일
│   ├── example_usage.py       # 사용 예시
│   └── utils/                 # 유틸리티 모듈
│       ├── io_utils.py        # 파일 I/O
│       ├── proposals.py       # 객체 제안
│       ├── taxonomy.py        # 택소노미 관리
│       └── exporters.py       # 결과 내보내기
├── config.yaml               # 설정 파일
├── requirements.txt          # 의존성
└── README.md                # 이 파일
```

## 🛠️ 설치

1. **의존성 설치**:
```bash
pip install -r requirements.txt
```

2. **환경변수 설정**:
```bash
# OpenAI 사용 시
export OPENAI_API_KEY="your-api-key"
export PROVIDER="openai"
export OPENAI_MODEL_VISION="gpt-4-vision-preview"

# DeepSeek 사용 시
export DEEPSEEK_API_KEY="your-api-key"
export PROVIDER="deepseek"
export DEEPSEEK_MODEL_VISION="deepseek-vision"
```

## 📖 사용법

### CLI 사용

```bash
# 단일 이미지 분석
python src/main.py --images diagram.png

# 디렉터리 내 모든 이미지 분석
python src/main.py --images-dir ./images

# 출력 형식 지정
python src/main.py --format labelstudio

# 테스트 모드 (API 키 불필요)
python src/main.py --test
```

### Python API 사용

```python
from src.llm_auto_labeler import AWSLLMAutoLabeler

# 초기화
labeler = AWSLLMAutoLabeler("config.yaml")

# 단일 이미지 분석
result = labeler.analyze_image("diagram.png")
print(f"감지된 객체: {len(result.detections)}개")

# 배치 분석
results = labeler.analyze_batch(["img1.png", "img2.png"])

# 결과 내보내기
labeler.export_results(results, "output/", "json")
```

## ⚙️ 설정

`config.yaml` 파일에서 다음 설정을 조정할 수 있습니다:

```yaml
project_name: aws_llm_autolabel
provider: ${PROVIDER}         # openai | deepseek
mode: ${MODE}                  # full_image_llm | patch_llm

openai:
  vision_model: ${OPENAI_MODEL_VISION}

deepseek:
  vision_model: ${DEEPSEEK_MODEL_VISION}

data:
  images_dir: ./images
  taxonomy_csv: ./aws_resources_models.csv

runtime:
  conf_threshold: ${CONF_THRESHOLD}  # 신뢰도 임계값

output:
  dir: ./out
  format: ${OUT_FORMAT}        # json | yolo | coco | labelstudio
```

## 🔄 aws_cv_clip과의 비교

| 특성 | aws_llm_autolabel | aws_cv_clip |
|------|------------------|-------------|
| **접근법** | LLM Vision API | Computer Vision (CLIP + ORB) |
| **비용** | API 호출 비용 | 무료 (로컬 처리) |
| **속도** | API 응답 시간 의존 | 로컬 GPU/CPU 처리 |
| **정확도** | LLM의 맥락적 이해 | 아이콘 매칭 기반 |
| **확장성** | 새로운 Vision 모델 지원 | 모델 재학습 필요 |

## 🧪 테스트

```bash
# 테스트 모드로 실행
python src/main.py --test

# 사용 예시 실행
python src/example_usage.py
```

## 📊 출력 형식

### JSON 형식
```json
[
  {
    "image_path": "diagram.png",
    "width": 800,
    "height": 600,
    "objects": [
      {
        "bbox": [100, 100, 50, 50],
        "label": "Amazon S3",
        "score": 0.85
      }
    ]
  }
]
```

### Label Studio 형식
```json
[
  {
    "data": {
      "image": "/data/local-files/?d=diagram.png"
    },
    "annotations": [
      {
        "result": [
          {
            "value": {
              "x": 12.5,
              "y": 16.7,
              "width": 6.25,
              "height": 8.33,
              "rectanglelabels": ["Amazon S3"]
            }
          }
        ]
      }
    ]
  }
]
```

## 🤝 기여

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

MIT License

## 🆘 문제 해결

### 일반적인 문제

1. **API 키 오류**: 환경변수가 올바르게 설정되었는지 확인
2. **메모리 부족**: 이미지 크기를 줄이거나 배치 크기 조정
3. **네트워크 오류**: API 엔드포인트와 인터넷 연결 확인

### 디버깅

```bash
# 상세 로그 활성화
export DEBUG=1
python src/main.py --images test.png
```

## 📞 지원

문제가 발생하면 GitHub Issues에 등록해 주세요.
