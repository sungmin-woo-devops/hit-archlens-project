#!/usr/bin/env python3
"""
AWS LLM 오토라벨러 메인 실행 파일
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List

from llm_auto_labeler import AWSLLMAutoLabeler

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="AWS LLM 기반 다이어그램 오토라벨러")
    parser.add_argument("--config", "-c", default="config.yaml", 
                       help="설정 파일 경로")
    parser.add_argument("--images", "-i", nargs="+", 
                       help="분석할 이미지 파일들")
    parser.add_argument("--images-dir", "-d", 
                       help="이미지 디렉터리")
    parser.add_argument("--output", "-o", default="./out", 
                       help="출력 디렉터리")
    parser.add_argument("--format", "-f", default="json", 
                       choices=["json", "yolo", "coco", "labelstudio"],
                       help="출력 형식")
    parser.add_argument("--test", action="store_true", 
                       help="테스트 모드 (Mock 제공자 사용)")
    
    args = parser.parse_args()
    
    # 설정 파일 경로 확인
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent.parent / args.config
    
    if not config_path.exists():
        print(f"❌ 설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)
    
    # 이미지 경로 수집
    image_paths = []
    
    if args.images:
        image_paths.extend(args.images)
    
    if args.images_dir:
        images_dir = Path(args.images_dir)
        if not images_dir.is_absolute():
            images_dir = Path(__file__).parent.parent / args.images_dir
        
        if images_dir.exists():
            from utils.io_utils import list_images
            image_paths.extend(list_images(str(images_dir)))
        else:
            print(f"⚠️ 이미지 디렉터리를 찾을 수 없습니다: {images_dir}")
    
    # 설정에서 이미지 디렉터리 확인
    if not image_paths:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        images_dir = Path(config.get("data", {}).get("images_dir", "./images"))
        if not images_dir.is_absolute():
            images_dir = Path(__file__).parent.parent / images_dir
        
        if images_dir.exists():
            from utils.io_utils import list_images
            image_paths = list_images(str(images_dir))
    
    if not image_paths:
        print("❌ 분석할 이미지를 찾을 수 없습니다.")
        print("   --images 또는 --images-dir 옵션을 사용하거나")
        print("   config.yaml의 images_dir에 이미지를 배치하세요.")
        sys.exit(1)
    
    print(f"📁 분석할 이미지: {len(image_paths)}개")
    for path in image_paths[:3]:  # 처음 3개만 표시
        print(f"   - {path}")
    if len(image_paths) > 3:
        print(f"   ... 외 {len(image_paths) - 3}개")
    
    # 테스트 모드 설정
    if args.test:
        os.environ["PROVIDER"] = "mock"
        print("🧪 테스트 모드 활성화 (Mock 제공자 사용)")
    
    try:
        # LLM 오토라벨러 초기화
        labeler = AWSLLMAutoLabeler(str(config_path))
        
        # 배치 분석 실행
        print(f"🚀 LLM 분석 시작...")
        results = labeler.analyze_batch(image_paths)
        
        if not results:
            print("❌ 분석 결과가 없습니다.")
            sys.exit(1)
        
        # 결과 내보내기
        output_dir = Path(args.output)
        if not output_dir.is_absolute():
            output_dir = Path(__file__).parent.parent / args.output
        
        output_path = labeler.export_results(results, str(output_dir), args.format)
        
        # 통계 출력
        stats = labeler.get_statistics(results)
        print(f"\n📊 분석 통계:")
        print(f"   - 총 이미지: {stats['total_images']}개")
        print(f"   - 총 감지: {stats['total_detections']}개")
        print(f"   - 이미지당 평균: {stats['avg_detections_per_image']:.1f}개")
        print(f"   - 평균 처리 시간: {stats['avg_processing_time']:.2f}초")
        
        print(f"\n🎯 신뢰도 분포:")
        print(f"   - 높음 (≥0.8): {stats['confidence_distribution']['high']}개")
        print(f"   - 중간 (0.5-0.8): {stats['confidence_distribution']['medium']}개")
        print(f"   - 낮음 (<0.5): {stats['confidence_distribution']['low']}개")
        
        if stats['service_distribution']:
            print(f"\n🏷️ 상위 서비스:")
            sorted_services = sorted(stats['service_distribution'].items(), 
                                   key=lambda x: x[1], reverse=True)
            for service, count in sorted_services[:5]:
                print(f"   - {service}: {count}개")
        
        print(f"\n✅ 분석 완료! 결과: {output_path}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
