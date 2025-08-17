# 바운딩 박스 시각화 도구

AWS 아키텍처 다이어그램에서 감지된 객체들의 바운딩 박스를 이미지와 겹쳐서 시각화하는 도구입니다.

## 설치

필요한 패키지를 설치합니다:

```bash
pip install -r requirements_visualization.txt
```

## 사용법

### 1. 기본 사용법 (첫 번째 이미지 시각화)

```bash
python visualize_bbox.py
```

### 2. 특정 이미지 시각화

```bash
python visualize_bbox.py --image cf3ed5f25c.png
```

### 3. 랜덤 이미지 선택하여 시각화

```bash
python visualize_bbox.py --random
```

### 4. 모든 이미지 처리하여 저장

```bash
python visualize_bbox.py --all
```

### 5. 처리 가능한 이미지 목록 확인

```bash
python visualize_bbox.py --list
```

### 6. 이미지를 파일로 저장

```bash
python visualize_bbox.py --image cf3ed5f25c.png --save output.png
```

### 7. 라벨이나 점수 숨기기

```bash
# 라벨 숨기기
python visualize_bbox.py --image cf3ed5f25c.png --no-labels

# 점수 숨기기
python visualize_bbox.py --image cf3ed5f25c.png --no-scores

# 라벨과 점수 모두 숨기기
python visualize_bbox.py --image cf3ed5f25c.png --no-labels --no-scores
```

## 명령행 옵션

- `--results`: results.json 파일 경로 (기본값: `out/results.json`)
- `--images-dir`: 이미지 디렉토리 경로 (기본값: `images`)
- `--image`: 특정 이미지 파일명
- `--random`: 랜덤 이미지 선택
- `--all`: 모든 이미지 처리
- `--output-dir`: 출력 디렉토리 (기본값: `out/visualizations`)
- `--save`: 저장할 파일 경로
- `--no-labels`: 라벨 숨기기
- `--no-scores`: 점수 숨기기
- `--list`: 처리 가능한 이미지 목록 출력

## 출력 예시

시각화된 이미지에는 다음 요소들이 포함됩니다:

1. **바운딩 박스**: 감지된 객체를 둘러싸는 컬러 박스
2. **라벨**: 객체의 이름 (예: "lambda", "cloudwatch")
3. **점수**: 감지 신뢰도 (0.0 ~ 1.0)
4. **범례**: 카테고리별 색상 매핑
5. **제목**: 이미지 파일명과 크기 정보

## 카테고리별 색상

각 AWS 서비스 카테고리별로 고유한 색상이 할당됩니다:

- `Arch_Management-Governance`: 관리 및 거버넌스 아키텍처
- `Arch_Compute`: 컴퓨팅 아키텍처
- `Res_General-Icons`: 일반 리소스 아이콘
- 기타 카테고리들...

## 예시 명령어

```bash
# 특정 이미지 시각화하여 파일로 저장
python visualize_bbox.py --image aws_diagram_sample_001.png --save sample_001_bbox.png

# 모든 이미지를 시각화하여 out/visualizations 디렉토리에 저장
python visualize_bbox.py --all

# 라벨만 표시하고 점수는 숨기기
python visualize_bbox.py --random --no-scores

# 처리 가능한 이미지 목록 확인
python visualize_bbox.py --list
```

## 파일 구조

```
aws_cv_clip/
├── visualize_bbox.py              # 메인 시각화 스크립트
├── requirements_visualization.txt # 필요한 패키지 목록
├── README_visualization.md        # 이 파일
├── out/
│   ├── results.json              # 감지 결과
│   └── visualizations/           # 시각화 결과 저장 디렉토리
└── images/                       # 원본 이미지들
    ├── cf3ed5f25c.png
    ├── aws_diagram_sample_001.png
    └── ...
```
