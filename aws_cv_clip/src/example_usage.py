"""
AWS 다이어그램 오토라벨러 사용 예시
"""

import os
from pathlib import Path
from aws_diagram_auto_labeler import AWSDiagramAutoLabeler

def main():
    """메인 사용 예시"""
    
    # 설정
    config = {
        "clip_name": "ViT-B-32",
        "clip_pretrained": "openai",
        "detect": {
            "max_size": 1600,
            "canny_low": 60,
            "canny_high": 160,
            "mser_delta": 5,
            "min_area": 900,
            "max_area": 90000,
            "win": 128,
            "stride": 96,
            "iou_nms": 0.45
        },
        "retrieval": {
            "topk": 5,
            "orb_nfeatures": 500,
            "score_clip_w": 0.6,
            "score_orb_w": 0.3,
            "score_ocr_w": 0.1,
            "accept_score": 0.5
        },
        "ocr": {
            "enabled": True,
            "lang": ["en"]
        }
    }
    
    # 경로 설정
    icons_dir = "path/to/aws/icons"
    taxonomy_csv = "path/to/taxonomy.csv"
    images_dir = "path/to/diagrams"
    output_dir = "path/to/output"
    
    # 오토라벨러 초기화
    print("🚀 AWS 다이어그램 오토라벨러 초기화 중...")
    labeler = AWSDiagramAutoLabeler(
        icons_dir=icons_dir,
        taxonomy_csv=taxonomy_csv,
        config=config
    )
    
    # 이미지 목록 생성
    image_extensions = [".png", ".jpg", ".jpeg", ".webp"]
    image_paths = []
    
    for ext in image_extensions:
        image_paths.extend(Path(images_dir).glob(f"*{ext}"))
        image_paths.extend(Path(images_dir).glob(f"*{ext.upper()}"))
    
    image_paths = [str(p) for p in image_paths]
    print(f"📁 발견된 이미지: {len(image_paths)}개")
    
    if not image_paths:
        print("❌ 분석할 이미지가 없습니다!")
        return
    
    # 배치 분석 실행
    print("🔍 다이어그램 분석 시작...")
    results = labeler.analyze_batch(image_paths)
    
    if not results:
        print("❌ 분석 결과가 없습니다!")
        return
    
    # 통계 출력
    stats = labeler.get_statistics(results)
    print("\n📊 분석 통계:")
    print(f"   - 총 이미지: {stats['total_images']}개")
    print(f"   - 총 탐지: {stats['total_detections']}개")
    print(f"   - 평균 처리 시간: {stats['avg_processing_time']:.2f}초")
    print(f"   - 탐지율: {stats['detection_rate']:.2f}")
    
    print("\n🏷️ 서비스별 탐지 분포:")
    for service, count in sorted(stats['service_distribution'].items(), 
                                key=lambda x: x[1], reverse=True)[:10]:
        print(f"   - {service}: {count}개")
    
    # 결과 내보내기
    print("\n💾 결과 내보내기 중...")
    
    # JSON 형식
    json_path = labeler.export_results(results, output_dir, format="json")
    print(f"   ✅ JSON: {json_path}")
    
    # YOLO 형식
    yolo_path = labeler.export_results(results, output_dir, format="yolo")
    print(f"   ✅ YOLO: {yolo_path}")
    
    # Label Studio 형식
    ls_path = labeler.export_results(results, output_dir, format="labelstudio")
    print(f"   ✅ Label Studio: {ls_path}")
    
    print(f"\n🎉 분석 완료! 결과는 {output_dir}에 저장되었습니다.")

def single_image_example():
    """단일 이미지 분석 예시"""
    
    config = {
        "clip_name": "ViT-B-32",
        "clip_pretrained": "openai",
        "detect": {
            "max_size": 1600,
            "canny_low": 60,
            "canny_high": 160,
            "mser_delta": 5,
            "min_area": 900,
            "max_area": 90000,
            "win": 128,
            "stride": 96,
            "iou_nms": 0.45
        },
        "retrieval": {
            "topk": 5,
            "orb_nfeatures": 500,
            "score_clip_w": 0.6,
            "score_orb_w": 0.3,
            "score_ocr_w": 0.1,
            "accept_score": 0.5
        },
        "ocr": {
            "enabled": True,
            "lang": ["en"]
        }
    }
    
    # 오토라벨러 초기화
    labeler = AWSDiagramAutoLabeler(
        icons_dir="path/to/aws/icons",
        taxonomy_csv="path/to/taxonomy.csv",
        config=config
    )
    
    # 단일 이미지 분석
    image_path = "path/to/single_diagram.png"
    result = labeler.analyze_image(image_path)
    
    print(f"📊 분석 결과: {image_path}")
    print(f"   - 이미지 크기: {result.width}x{result.height}")
    print(f"   - 처리 시간: {result.processing_time:.2f}초")
    print(f"   - 탐지된 아이콘: {len(result.detections)}개")
    
    for i, detection in enumerate(result.detections, 1):
        print(f"   {i}. {detection.label} (신뢰도: {detection.confidence:.3f})")
        print(f"      - 바운딩 박스: {detection.bbox}")
        print(f"      - 서비스 코드: {detection.service_code}")

def custom_config_example():
    """커스텀 설정 예시"""
    
    # 고정밀도 설정 (더 정확하지만 느림)
    high_precision_config = {
        "clip_name": "ViT-L-14",
        "clip_pretrained": "openai",
        "detect": {
            "max_size": 2048,
            "canny_low": 50,
            "canny_high": 150,
            "mser_delta": 3,
            "min_area": 600,
            "max_area": 120000,
            "win": 96,
            "stride": 64,
            "iou_nms": 0.4
        },
        "retrieval": {
            "topk": 10,
            "orb_nfeatures": 1000,
            "score_clip_w": 0.7,
            "score_orb_w": 0.25,
            "score_ocr_w": 0.05,
            "accept_score": 0.6
        },
        "ocr": {
            "enabled": True,
            "lang": ["en", "ko"]
        }
    }
    
    # 고속 설정 (빠르지만 덜 정확)
    fast_config = {
        "clip_name": "ViT-B-16",
        "clip_pretrained": "openai",
        "detect": {
            "max_size": 1200,
            "canny_low": 70,
            "canny_high": 170,
            "mser_delta": 7,
            "min_area": 1200,
            "max_area": 60000,
            "win": 160,
            "stride": 128,
            "iou_nms": 0.5
        },
        "retrieval": {
            "topk": 3,
            "orb_nfeatures": 300,
            "score_clip_w": 0.8,
            "score_orb_w": 0.2,
            "score_ocr_w": 0.0,
            "accept_score": 0.4
        },
        "ocr": {
            "enabled": False,
            "lang": ["en"]
        }
    }
    
    # 설정에 따른 오토라벨러 초기화
    labeler = AWSDiagramAutoLabeler(
        icons_dir="path/to/aws/icons",
        taxonomy_csv="path/to/taxonomy.csv",
        config=high_precision_config  # 또는 fast_config
    )

if __name__ == "__main__":
    main()
