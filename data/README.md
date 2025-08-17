# Data Directory

이 디렉터리는 Hit ArchLens에서 수집된 클라우드 데이터를 저장합니다.

## 구조

```
data/
├── aws/                    # AWS 데이터
│   ├── icons/             # AWS 아이콘 매핑
│   ├── services/          # AWS 서비스 정보
│   ├── products/          # AWS 제품 정보
│   ├── taxonomy/          # AWS 분류 체계
│   └── unified/           # 통합 데이터
├── gcp/                    # GCP 데이터 (향후)
├── azure/                  # Azure 데이터 (향후)
└── naver/                  # Naver Cloud 데이터 (향후)
```

## 파일 형식

- **CSV**: 구조화된 데이터 (Excel 호환)
- **JSON**: 프로그래밍 인터페이스용
- **YAML**: 설정 및 메타데이터

## 데이터 소스

- **Icons**: AWS 공식 아이콘 패키지
- **Services**: boto3 API 메타데이터
- **Products**: AWS 제품 API
- **Taxonomy**: 서비스 분류 및 정규화 규칙
