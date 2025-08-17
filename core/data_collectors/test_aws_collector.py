"""
AWS Data Collector 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.data_collectors import AWSDataCollector


def test_aws_collector():
    """AWS Data Collector 테스트"""
    print("�� AWS Data Collector 테스트 시작")
    
    # 설정
    config = {
        "aws": {
            "region": "us-east-1"
        },
        "collectors": {
            "icons": {
                "zip_path": "Asset-Package.zip",
                "output_dir": "data/aws/icons"
            },
            "services": {
                "output_dir": "data/aws/services"
            },
            "products": {
                "api_url": "https://aws.amazon.com/api/dirs/items/search?item.directoryId=aws-products&sort_by=item.additionalFields.productNameLowercase&size=1000&language=en&item.locale=en_US",
                "output_dir": "data/aws/products"
            }
        }
    }
    
    # 수집기 생성
    collector = AWSDataCollector(config)
    
    # 지원 데이터 타입 확인
    supported_types = collector.get_supported_data_types()
    print(f"📋 지원 데이터 타입: {supported_types}")
    
    # 상태 확인
    status = collector.get_collection_status()
    print(f"�� 초기 상태: {status}")
    
    # 서비스 정보 수집 테스트 (아이콘과 제품은 파일 의존성으로 생략)
    print("\n🔍 서비스 정보 수집 테스트")
    try:
        result = collector.collect_specific("services")
        print(f"  성공: {result.success}")
        print(f"  데이터 수: {result.data_count}")
        print(f"  처리 시간: {result.processing_time:.2f}초")
        print(f"  출력 파일: {result.output_paths}")
        
        if result.errors:
            print(f"  오류: {result.errors}")
            
    except Exception as e:
        print(f"  ❌ 서비스 수집 실패: {e}")
    
    # 통계 확인
    stats = collector.collection_stats
    print(f"\n�� 수집 통계:")
    print(f"  총 수집: {stats.total_collections}")
    print(f"  성공: {stats.successful_collections}")
    print(f"  실패: {stats.failed_collections}")
    print(f"  성공률: {stats.success_rate:.2%}")
    
    print("\n✅ AWS Data Collector 테스트 완료")


if __name__ == "__main__":
    test_aws_collector()
