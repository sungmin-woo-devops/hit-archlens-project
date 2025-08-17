"""
출력 디렉터리 구조 설정 스크립트

모든 결과물을 out/ 디렉터리에 통합 저장
"""

import shutil
from pathlib import Path
from typing import List, Dict, Any


def setup_output_structure():
    """출력 디렉터리 구조 설정"""
    print("📁 출력 디렉터리 구조 설정 시작")
    
    # 프로젝트 루트
    project_root = Path(__file__).parent.parent.parent
    
    # out 디렉터리 구조
    output_structure = {
        "out": {
            # AWS 데이터 수집 결과
            "aws": {
                "icons": {},
                "services": {},
                "products": {},
                "taxonomy": {}
            },
            # 실험 결과
            "experiments": {
                "cv_results": {},
                "llm_results": {},
                "hybrid_results": {},
                "batch_results": {}
            },
            # 시각화 결과
            "visualizations": {
                "charts": {},
                "reports": {},
                "dashboards": {}
            },
            # 성능 평가 결과
            "evaluation": {
                "metrics": {},
                "comparisons": {},
                "benchmarks": {}
            },
            # 통계 및 분석
            "statistics": {
                "collection_stats": {},
                "analysis_stats": {},
                "performance_stats": {}
            }
        }
    }
    
    # 디렉터리 생성
    dir_paths = _flatten_structure(output_structure, project_root)
    for dir_path in dir_paths:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  📁 생성: {dir_path}")
    
    # 기존 파일들 마이그레이션
    migrate_existing_files(project_root)
    
    print("✅ 출력 디렉터리 구조 설정 완료")


def _flatten_structure(structure: Dict, base_path: Path) -> List[Path]:
    """구조를 평면화하여 모든 디렉터리 경로 반환"""
    paths = []
    
    for name, content in structure.items():
        current_path = base_path / name
        paths.append(current_path)
        
        if isinstance(content, dict):
            paths.extend(_flatten_structure(content, current_path))
    
    return paths


def migrate_existing_files(project_root: Path):
    """기존 파일들을 out/ 디렉터리로 마이그레이션"""
    print("✅ 기존 파일 마이그레이션 시작")
    
    # 마이그레이션 매핑
    migrations = [
        # 기존 taxonomy 파일들
        ("out/aws_resources_models.csv", "out/aws/taxonomy/aws_resources_models.csv"),
        ("out/aws_resources_models.json", "out/aws/taxonomy/aws_resources_models.json"),
        
        # 기존 data/aws/ 파일들 (있다면)
        ("data/aws/icons/", "out/aws/icons/"),
        ("data/aws/services/", "out/aws/services/"),
        ("data/aws/products/", "out/aws/products/"),
    ]
    
    for source, dest in migrations:
        source_path = project_root / source
        dest_path = project_root / dest
        
        if source_path.exists():
            if source_path.is_file():
                # 파일 복사
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, dest_path)
                print(f"  📄 복사: {source} → {dest}")
            elif source_path.is_dir():
                # 디렉터리 복사
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(source_path, dest_path)
                print(f"  📁 복사: {source} → {dest}")


if __name__ == "__main__":
    setup_output_structure()
