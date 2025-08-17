"""
데이터 저장소 구조 설정 스크립트
"""

import shutil
from pathlib import Path
from typing import List, Dict, Any


def setup_data_structure():
    """데이터 저장소 구조 설정"""
    print("📁 데이터 저장소 구조 설정 시작")
    
    # 프로젝트 루트
    project_root = Path(__file__).parent.parent.parent
    
    # 데이터 디렉터리 구조
    data_structure = {
        "data": {
            "aws": {
                "icons": {},
                "services": {},
                "products": {},
                "taxonomy": {},
                "unified": {}
            },
            "gcp": {
                "icons": {},
                "services": {},
                "products": {},
                "taxonomy": {},
                "unified": {}
            },
            "azure": {
                "icons": {},
                "services": {},
                "products": {},
                "taxonomy": {},
                "unified": {}
            },
            "naver": {
                "icons": {},
                "services": {},
                "products": {},
                "taxonomy": {},
                "unified": {}
            }
        }
    }
    
    # 디렉터리 생성
    for cloud_provider, subdirs in data_structure["data"].items():
        for subdir in subdirs:
            dir_path = project_root / "data" / cloud_provider / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  📁 생성: {dir_path}")
    
    # README 파일 생성
    readme_content = """# Data Directory

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
"""
    
    readme_path = project_root / "data" / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"  📄 생성: {readme_path}")
    print("✅ 데이터 저장소 구조 설정 완료")


def migrate_existing_data():
    """기존 데이터 마이그레이션"""
    print("🔄 기존 데이터 마이그레이션 시작")
    
    project_root = Path(__file__).parent.parent.parent
    
    # 마이그레이션 매핑
    migration_mapping = {
        # AWS 데이터
        "aws_llm_autolabel/aws_resources_models.csv": "data/aws/taxonomy/aws_resources_models.csv",
        "aws_cv_clip/aws_resources_models.csv": "data/aws/taxonomy/aws_resources_models_cv.csv",
        "out/aws_resources_models.csv": "data/aws/taxonomy/aws_resources_models_out.csv",
        
        # AWS 데이터 수집기 결과
        "aws_data_collectors/data/icons/": "data/aws/icons/",
        "aws_data_collectors/data/services/": "data/aws/services/",
        "aws_data_collectors/data/products/": "data/aws/products/",
    }
    
    for source, destination in migration_mapping.items():
        source_path = project_root / source
        dest_path = project_root / destination
        
        if source_path.exists():
            try:
                if source_path.is_file():
                    # 파일 복사
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                    print(f"  📄 복사: {source} → {destination}")
                elif source_path.is_dir():
                    # 디렉터리 복사
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                    print(f"  📁 복사: {source} → {destination}")
            except Exception as e:
                print(f"  ❌ 마이그레이션 실패: {source} - {e}")
        else:
            print(f"  ⚠️ 소스 파일 없음: {source}")
    
    print("✅ 기존 데이터 마이그레이션 완료")


if __name__ == "__main__":
    setup_data_structure()
    migrate_existing_data()
