"""
AWS Taxonomy 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.taxonomy import AWSTaxonomy


def test_aws_taxonomy():
    """AWS Taxonomy 테스트"""
    print("🧪 AWS Taxonomy 테스트 시작")
    
    # Taxonomy 인스턴스 생성
    taxonomy = AWSTaxonomy()
    
    # CSV 파일 경로 (기존 파일 사용)
    csv_path = "aws_llm_autolabel/aws_resources_models.csv"
    
    if not Path(csv_path).exists():
        print(f"❌ CSV 파일을 찾을 수 없습니다: {csv_path}")
        return False
    
    # 데이터 로드
    print(f"📂 CSV 파일 로드: {csv_path}")
    success = taxonomy.load_from_source(csv_path)
    
    if not success:
        print("❌ 데이터 로드 실패")
        return False
    
    # 통계 정보 출력
    stats = taxonomy.get_statistics()
    print(f"📊 통계: {stats}")
    
    # 유효성 검증
    is_valid, errors = taxonomy.validate()
    if not is_valid:
        print(f"⚠️ 유효성 검증 실패: {errors}")
    else:
        print("✅ 유효성 검증 통과")
    
    # 정규화 테스트
    test_cases = [
        "Amazon EC2",
        "EC2",
        "ec2",
        "Amazon Simple Storage Service",
        "S3",
        "s3",
        "AWS Lambda",
        "Lambda",
        "lambda",
        "Amazon RDS",
        "RDS",
        "rds",
        "Unknown Service",
        ""
    ]
    
    print("\n�� 정규화 테스트:")
    for test_case in test_cases:
        result = taxonomy.normalize(test_case)
        print(f"  '{test_case}' -> '{result.canonical_name}' (신뢰도: {result.confidence:.2f})")
    
    # 서비스 그룹 테스트
    print("\n��️ 서비스 그룹 테스트:")
    for service in ["Amazon EC2", "Amazon S3", "AWS Lambda"]:
        group = taxonomy.get_service_group(service)
        code = taxonomy.get_service_code(service)
        print(f"  {service}: 그룹={group}, 코드={code}")
    
    print("\n✅ AWS Taxonomy 테스트 완료")
    return True


if __name__ == "__main__":
    test_aws_taxonomy()
