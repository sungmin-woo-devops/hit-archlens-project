#!/usr/bin/env python3
"""
AWS 아이콘 웹 수집기 사용 예시
Scrapy를 사용하여 웹에서 AWS 아이콘을 수집하고 훈련 데이터셋을 보강하는 방법을 보여줍니다.
"""

import json
import time
from pathlib import Path
from typing import List, Dict

# 수집기 임포트
from scrapy_icon_collector import ScrapyIconCollector, WebIconData

def example_basic_collection():
    """기본 아이콘 수집 예시"""
    print("=== 기본 아이콘 수집 예시 ===")
    
    # 수집기 초기화
    collector = ScrapyIconCollector(output_dir="example_collected_icons")
    
    # 특정 서비스 아이콘 수집
    service_name = "EC2"
    queries = collector.generate_search_queries(service_name)
    
    print(f"'{service_name}' 서비스 검색 쿼리:")
    for i, query in enumerate(queries, 1):
        print(f"  {i}. {query}")
    
    # Google Images에서 수집 (시뮬레이션)
    icons = collector.collect_from_google_images(queries[0], max_results=3)
    
    print(f"\n수집된 아이콘: {len(icons)}개")
    for icon in icons:
        print(f"  - {icon.service_name}: {icon.file_path} ({icon.image_width}x{icon.image_height})")
    
    # 결과 저장
    collector.save_collection(icons, "example_icons.json")
    
    # 통계 출력
    stats = collector.get_statistics(icons)
    print(f"\n통계:")
    print(f"  총 아이콘 수: {stats['total_icons']}")
    print(f"  평균 신뢰도: {stats.get('avg_confidence', 0):.2f}")

def example_github_collection():
    """GitHub에서 아이콘 수집 예시"""
    print("\n=== GitHub 아이콘 수집 예시 ===")
    
    collector = ScrapyIconCollector(output_dir="example_github_icons")
    
    # GitHub 저장소에서 수집
    icons = collector.collect_from_github_aws_icons()
    
    print(f"GitHub에서 수집된 아이콘: {len(icons)}개")
    
    # 고품질 아이콘만 필터링
    high_quality = collector.filter_high_quality_icons(
        icons, 
        min_confidence=0.8, 
        min_size=1000
    )
    
    print(f"고품질 아이콘: {len(high_quality)}개")
    
    # 결과 저장
    collector.save_collection(high_quality, "github_high_quality_icons.json")

def example_all_services_collection():
    """모든 AWS 서비스 아이콘 수집 예시"""
    print("\n=== 모든 AWS 서비스 아이콘 수집 예시 ===")
    
    collector = ScrapyIconCollector(output_dir="example_all_services")
    
    # 주요 서비스들만 수집 (전체는 시간이 오래 걸림)
    important_services = ["EC2", "S3", "Lambda", "RDS", "DynamoDB", "CloudFront", "VPC"]
    
    all_icons = []
    for service in important_services:
        print(f"\n{service} 아이콘 수집 중...")
        
        queries = collector.generate_search_queries(service)
        for query in queries[:2]:  # 상위 2개 쿼리만 사용
            try:
                icons = collector.collect_from_google_images(query, max_results=2)
                all_icons.extend(icons)
                time.sleep(1)  # 요청 간격 조절
            except Exception as e:
                print(f"  수집 실패: {e}")
    
    print(f"\n총 수집된 아이콘: {len(all_icons)}개")
    
    # 고품질 아이콘 필터링
    high_quality = collector.filter_high_quality_icons(all_icons)
    print(f"고품질 아이콘: {len(high_quality)}개")
    
    # 결과 저장
    collector.save_collection(high_quality, "all_services_high_quality.json")
    
    # 서비스별 통계
    stats = collector.get_statistics(high_quality)
    print(f"\n서비스별 분포:")
    for service, count in sorted(stats['services'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {service}: {count}개")

def example_data_analysis():
    """수집된 데이터 분석 예시"""
    print("\n=== 데이터 분석 예시 ===")
    
    # 수집된 데이터 읽기
    data_file = "example_all_services/all_services_high_quality.json"
    
    if Path(data_file).exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            icons = json.load(f)
        
        print(f"분석 대상 아이콘: {len(icons)}개")
        
        # 파일 크기 분석
        file_sizes = [icon['file_size'] for icon in icons]
        avg_size = sum(file_sizes) / len(file_sizes)
        print(f"평균 파일 크기: {avg_size:.0f} bytes")
        
        # 이미지 크기 분석
        widths = [icon['image_width'] for icon in icons]
        heights = [icon['image_height'] for icon in icons]
        print(f"평균 이미지 크기: {sum(widths)/len(widths):.0f}x{sum(heights)/len(heights):.0f}")
        
        # 신뢰도 분석
        confidences = [icon['confidence_score'] for icon in icons]
        avg_confidence = sum(confidences) / len(confidences)
        print(f"평균 신뢰도: {avg_confidence:.2f}")
        
        # 소스별 분석
        sources = {}
        for icon in icons:
            source = icon['source_url']
            sources[source] = sources.get(source, 0) + 1
        
        print(f"\n소스별 분포:")
        for source, count in sources.items():
            print(f"  {source}: {count}개")
    
    else:
        print(f"데이터 파일이 없습니다: {data_file}")

def example_integration_with_existing():
    """기존 시스템과의 통합 예시"""
    print("\n=== 기존 시스템 통합 예시 ===")
    
    # 기존 아이콘 수집기와 통합
    from icon_collector import AWSIconCollector
    
    # 기존 ZIP 파일에서 아이콘 수집
    zip_collector = AWSIconCollector()
    zip_mappings = zip_collector.collect_icons("Asset-Package.zip")
    
    print(f"ZIP에서 수집된 아이콘: {len(zip_mappings)}개")
    
    # 웹에서 추가 아이콘 수집
    web_collector = ScrapyIconCollector(output_dir="integrated_icons")
    
    # ZIP에 없는 서비스들 찾기
    zip_services = {mapping.service for mapping in zip_mappings}
    all_services = set(web_collector.aws_services)
    missing_services = all_services - zip_services
    
    print(f"ZIP에 없는 서비스들: {len(missing_services)}개")
    print(f"  {', '.join(list(missing_services)[:10])}...")
    
    # 누락된 서비스들 웹에서 수집
    web_icons = []
    for service in list(missing_services)[:5]:  # 상위 5개만
        try:
            icons = web_collector.collect_from_google_images(f"AWS {service} icon", max_results=2)
            web_icons.extend(icons)
        except Exception as e:
            print(f"  {service} 수집 실패: {e}")
    
    print(f"웹에서 추가 수집된 아이콘: {len(web_icons)}개")
    
    # 통합 결과 저장
    web_collector.save_collection(web_icons, "integrated_web_icons.json")

def main():
    """메인 실행 함수"""
    print("AWS 아이콘 웹 수집기 사용 예시")
    print("=" * 50)
    
    try:
        # 기본 수집 예시
        example_basic_collection()
        
        # GitHub 수집 예시
        example_github_collection()
        
        # 모든 서비스 수집 예시
        example_all_services_collection()
        
        # 데이터 분석 예시
        example_data_analysis()
        
        # 기존 시스템 통합 예시
        example_integration_with_existing()
        
        print("\n" + "=" * 50)
        print("모든 예시 실행 완료!")
        print("\n수집된 아이콘들은 다음 디렉토리에서 확인할 수 있습니다:")
        print("  - example_collected_icons/")
        print("  - example_github_icons/")
        print("  - example_all_services/")
        print("  - integrated_icons/")
        
    except Exception as e:
        print(f"예시 실행 중 오류 발생: {e}")
        print("Scrapy와 관련 의존성이 설치되어 있는지 확인해주세요.")

if __name__ == "__main__":
    main()
