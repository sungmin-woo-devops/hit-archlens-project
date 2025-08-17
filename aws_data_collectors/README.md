# AWS 데이터 수집기 모듈

AWS 관련 데이터를 수집하고 처리하는 통합 모듈입니다. 기존의 세 개 폴더를 하나의 체계적인 모듈로 통합했습니다.

## 📁 **모듈 구조**

```
aws_data_collectors/
├── 📚 README.md                      # 이 문서
├── 📦 requirements.txt               # 의존성 패키지
├── ⚙️ config.yaml                    # 설정 파일
├── 🚀 main.py                        # 메인 실행 스크립트
│
├── 🔍 collectors/                    # 데이터 수집기들
│   ├── __init__.py
│   ├── icon_collector.py             # AWS 아이콘 수집기
│   ├── product_collector.py          # AWS 제품 정보 수집기
│   └── service_collector.py          # AWS 서비스 정보 수집기
│
├── 🛠️ processors/                    # 데이터 처리기들
│   ├── __init__.py
│   ├── icon_processor.py             # 아이콘 데이터 처리
│   ├── product_processor.py          # 제품 데이터 처리
│   └── service_processor.py          # 서비스 데이터 처리
│
├── 💾 exporters/                     # 데이터 내보내기
│   ├── __init__.py
│   ├── csv_exporter.py               # CSV 내보내기
│   ├── json_exporter.py              # JSON 내보내기
│   └── unified_exporter.py           # 통합 내보내기
│
├── 🔧 utils/                         # 유틸리티
│   ├── __init__.py
│   ├── file_utils.py                 # 파일 처리 유틸리티
│   ├── aws_utils.py                  # AWS 관련 유틸리티
│   └── validation.py                 # 데이터 검증
│
└── 📊 data/                          # 수집된 데이터
    ├── icons/                        # 아이콘 데이터
    ├── products/                     # 제품 데이터
    └── services/                     # 서비스 데이터
```

## 🎯 **주요 기능**

### **1. AWS 아이콘 수집기 (`icon_collector.py`)**
- AWS 공식 아이콘 ZIP 파일 파싱
- 아이콘 매핑 파일 생성 (CSV, JSON)
- 그룹별, 서비스별 아이콘 분류
- 정규화 및 중복 제거

### **2. AWS 제품 정보 수집기 (`product_collector.py`)**
- AWS 공식 API에서 제품 정보 수집
- 제품 카테고리, 이름, URL 정보 추출
- JSON 및 CSV 형식으로 저장

### **3. AWS 서비스 정보 수집기 (`service_collector.py`)**
- boto3를 통한 AWS 서비스 메타데이터 수집
- 서비스 코드, 전체 이름, 리전 정보 추출
- 대표 리소스 예시 자동 추론

## 🚀 **사용법**

### **기본 사용법**
```python
from aws_data_collectors.main import AWSDataCollector

# 데이터 수집기 초기화
collector = AWSDataCollector()

# 모든 데이터 수집
collector.collect_all()

# 특정 데이터만 수집
collector.collect_icons()
collector.collect_products()
collector.collect_services()
```

### **설정 파일 사용**
```yaml
# config.yaml
collectors:
  icons:
    zip_path: "Asset-Package.zip"
    output_dir: "data/icons"
  products:
    api_url: "https://aws.amazon.com/api/dirs/items/search"
    output_dir: "data/products"
  services:
    output_dir: "data/services"

exporters:
  formats: ["csv", "json"]
  unified_output: "data/unified"
```

## 📊 **출력 데이터 형식**

### **아이콘 매핑**
```csv
group,category,service,zip_path
Compute,,Amazon EC2,Resource-Icons_02072025/Res_Compute/Res_Amazon-EC2_Instance_48.svg
Storage,,Amazon S3,Resource-Icons_02072025/Res_Storage/Res_Amazon-S3_Bucket_48.svg
```

### **제품 정보**
```csv
group,service,service_url
Compute,Amazon EC2,https://aws.amazon.com/ec2/
Storage,Amazon S3,https://aws.amazon.com/s3/
```

### **서비스 정보**
```csv
service_code,service_full_name,endpoint_prefix,regions,main_resource_example
ec2,Amazon Elastic Compute Cloud,ec2,us-east-1;us-west-2,Instance
s3,Amazon Simple Storage Service,s3,us-east-1;us-west-2,Bucket
```

## 🔧 **설치 및 설정**

### **1. 의존성 설치**
```bash
pip install -r requirements.txt
```

### **2. AWS 아이콘 다운로드**
```bash
# AWS 공식 아이콘 패키지 다운로드
wget https://aws.amazon.com/ko/architecture/icons/
```

### **3. 설정 파일 생성**
```bash
cp config.yaml.example config.yaml
# 설정 파일 편집
```

## 📈 **성능 최적화**

### **병렬 처리**
- 멀티프로세싱을 통한 동시 수집
- 비동기 API 호출
- 배치 처리 지원

### **캐싱**
- 수집된 데이터 캐싱
- 중복 수집 방지
- 증분 업데이트 지원

## 🔮 **향후 확장 계획**

### **Phase 1: 기본 기능** ✅
- [x] 아이콘 수집기
- [x] 제품 정보 수집기
- [x] 서비스 정보 수집기

### **Phase 2: 고도화** 🔄
- [ ] 실시간 데이터 수집
- [ ] 데이터 검증 강화
- [ ] 에러 처리 개선

### **Phase 3: 확장** 📈
- [ ] 다른 클라우드 서비스 지원
- [ ] 웹 인터페이스
- [ ] API 서비스화

## 🤝 **기여하기**

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 **라이선스**

MIT License
