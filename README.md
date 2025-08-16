# AWS Architecture Lens

AWS 서비스 및 리소스 분석을 위한 종합적인 도구 모음입니다. 이 프로젝트는 AWS 서비스 정보 수집, 아이콘 매핑, 서비스 코드 추출 및 데이터 파이프라인을 포함합니다.

## 📁 프로젝트 구조

```
hit_archlens/
├── aws_icons_parser/          # AWS 아이콘 패키지 파싱 및 매핑
├── aws_products_scraper/      # AWS 제품 정보 스크래핑
├── aws_service_boto3/         # Boto3를 통한 AWS 서비스 코드 추출
├── aws_services/              # Scrapy 기반 AWS 서비스 크롤링
├── aws-service-mapper/        # AWS 서비스 매핑 라이브러리
├── dags/                      # Apache Airflow DAG (RSS 수집)
└── out/                       # 출력 디렉토리
```

## 🚀 주요 기능

### 1. AWS 아이콘 파서 (`aws_icons_parser/`)
AWS 공식 아이콘 패키지를 파싱하여 서비스별 아이콘 매핑을 생성합니다.

```bash
cd aws_icons_parser
python aws_icons_zip_to_mapping.py Asset-Package.zip
```

**출력 파일:**
- `aws_icons_mapping.csv` - CSV 형식의 아이콘 매핑
- `aws_icons_mapping.json` - JSON 형식의 아이콘 매핑

### 2. AWS 서비스 코드 추출기 (`aws_service_boto3/`)
Boto3를 사용하여 AWS 서비스 메타데이터를 추출합니다.

```bash
cd aws_service_boto3
python export_service_codes.py
```

**출력 파일:**
- `aws_service_codes.csv` - 서비스 코드 및 메타데이터
- `aws_service_codes.json` - JSON 형식의 서비스 정보

### 3. AWS 제품 스크래퍼 (`aws_products_scraper/`)
AWS 제품 정보를 수집하고 정리합니다.

```bash
cd aws_products_scraper
# Scrapy 스파이더 실행
scrapy crawl products
```

### 4. RSS 수집 파이프라인 (`dags/`)
Apache Airflow를 사용한 RSS 피드 수집 및 처리 파이프라인입니다.

```bash
# Airflow 환경 설정
pip install apache-airflow[celery,postgres,redis]

# DAG 실행
airflow dags trigger rss_ingest_fast
```

## 🛠️ 설치 및 설정

### 필수 요구사항
- Python 3.10+
- Apache Airflow (RSS 파이프라인용)
- AWS CLI 및 Boto3 (서비스 코드 추출용)

### 가상환경 설정
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Linux/Mac)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### AWS 설정
```bash
# AWS 자격 증명 설정
aws configure

# 또는 환경 변수 설정
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

## 📊 데이터 파일

### 생성되는 주요 데이터 파일들:
- `aws_service_codes.json` - AWS 서비스 코드 및 메타데이터
- `aws_icons_mapping.json` - 서비스별 아이콘 매핑
- `aws_products.json` - AWS 제품 정보
- `aws_services.csv` - 정리된 서비스 목록

## 🔧 사용법

### 1. AWS 서비스 정보 수집
```bash
# 서비스 코드 추출
cd aws_service_boto3
python export_service_codes.py

# 제품 정보 스크래핑
cd aws_products_scraper
scrapy crawl products
```

### 2. 아이콘 매핑 생성
```bash
cd aws_icons_parser
python aws_icons_zip_to_mapping.py Asset-Package.zip
```

### 3. RSS 파이프라인 실행
```bash
# Airflow 웹서버 시작
airflow webserver --port 8080

# Airflow 스케줄러 시작
airflow scheduler

# DAG 수동 실행
airflow dags trigger rss_ingest_fast
```

## 📈 데이터 파이프라인

### RSS 수집 파이프라인 (`dags/rss_ingest.py`)
- **스케줄**: 15분마다 실행
- **기능**: RSS 피드 수집, 요약 생성, 데이터 정규화
- **태그**: `rss`, `news`, `ai`

### 워크플로우:
1. **fetch**: RSS 피드에서 데이터 수집
2. **normalize**: 스키마 정규화 및 해시 생성
3. **sink**: S3/Kafka/DB에 데이터 적재

## 🔍 데이터 분석

### 서비스 코드 분석
```bash
cd aws_service_boto3
python infer_from_models.py
```

### 아이콘 매핑 쿼리
```bash
cd aws_services
./test_query.sh
```

## 📝 개발 가이드라인

### 코드 스타일
- Python 3.10+ 타입 힌트 사용
- POSIX 호환 Bash 스크립트
- 함수형 컴포넌트 및 훅 사용 (React)

### 파일 구조
- 모듈화된 디렉토리 구조
- 명확한 네이밍 컨벤션
- 설정 파일 분리

### 테스트
- `pytest` 사용
- `shellcheck`로 스크립트 검증
- 정상 및 예외 케이스 커버

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🔗 관련 링크

- [AWS 공식 아이콘](https://aws.amazon.com/ko/architecture/icons/)
- [Boto3 문서](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Apache Airflow 문서](https://airflow.apache.org/docs/)

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해 주세요.
