#!/usr/bin/env python3
"""
AWS LLM 오토라벨러 사용 예시
"""

import os
from pathlib import Path
from llm_auto_labeler import AWSLLMAutoLabeler

def example_single_image():
    """단일 이미지 분석 예시"""
    print("=== 단일 이미지 분석 예시 ===")
    
    # LLM 오토라벨러 초기화
    labeler = AWSLLMAutoLabeler("config.yaml")
    
    # 단일 이미지 분석
    image_path = "images/aws_diagram_sample_001.png"
    if os.path.exists(image_path):
        result = labeler.analyze_image(image_path)
        
        print(f"📊 분석 결과:")
        print(f"   - 이미지: {result.image_path}")
        print(f"   - 크기: {result.width}x{result.height}")
        print(f"   - 감지된 객체: {len(result.detections)}개")
        print(f"   - 처리 시간: {result.processing_time:.2f}초")
        
        for i, detection in enumerate(result.detections, 1):
            print(f"   {i}. {detection.label} (신뢰도: {detection.confidence:.3f})")
            print(f"      바운딩 박스: {detection.bbox}")
    else:
        print(f"⚠️ 이미지 파일을 찾을 수 없습니다: {image_path}")

def example_batch_analysis():
    """배치 분석 예시"""
    print("\n=== 배치 분석 예시 ===")
    
    # LLM 오토라벨러 초기화
    labeler = AWSLLMAutoLabeler("config.yaml")
    
    # 이미지 디렉터리에서 모든 이미지 분석
    images_dir = "images"
    if os.path.exists(images_dir):
        image_paths = []
        for ext in ["*.png", "*.jpg", "*.jpeg"]:
            image_paths.extend(Path(images_dir).glob(ext))
        
        if image_paths:
            print(f"📁 분석할 이미지: {len(image_paths)}개")
            
            # 배치 분석 실행
            results = labeler.analyze_batch([str(p) for p in image_paths])
            
            # 통계 출력
            stats = labeler.get_statistics(results)
            print(f"\n📊 배치 분석 통계:")
            print(f"   - 총 이미지: {stats['total_images']}개")
            print(f"   - 총 감지: {stats['total_detections']}개")
            print(f"   - 이미지당 평균: {stats['avg_detections_per_image']:.1f}개")
            print(f"   - 평균 처리 시간: {stats['avg_processing_time']:.2f}초")
            
            # 결과 내보내기
            output_path = labeler.export_results(results, "out", "json")
            print(f"✅ 결과 저장: {output_path}")
        else:
            print(f"⚠️ 이미지 파일을 찾을 수 없습니다: {images_dir}")
    else:
        print(f"⚠️ 이미지 디렉터리를 찾을 수 없습니다: {images_dir}")

def example_custom_config():
    """사용자 정의 설정 예시"""
    print("\n=== 사용자 정의 설정 예시 ===")
    
    # 환경변수 설정 (실제 사용 시)
    os.environ["PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "your-api-key-here"
    os.environ["OPENAI_MODEL_VISION"] = "gpt-4-vision-preview"
    
    # 사용자 정의 설정으로 초기화
    custom_config = {
        "provider": "openai",
        "mode": "full_image_llm",
        "openai": {
            "vision_model": "gpt-4-vision-preview"
        },
        "runtime": {
            "conf_threshold": 0.7
        },
        "data": {
            "taxonomy_csv": "aws_resources_models.csv"
        }
    }
    
    # 임시 설정 파일 생성
    import yaml
    temp_config_path = "temp_config.yaml"
    with open(temp_config_path, "w") as f:
        yaml.dump(custom_config, f)
    
    try:
        labeler = AWSLLMAutoLabeler(temp_config_path)
        print("✅ 사용자 정의 설정으로 초기화 완료")
    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
    finally:
        # 임시 파일 정리
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)

def example_test_mode():
    """테스트 모드 예시"""
    print("\n=== 테스트 모드 예시 ===")
    
    # Mock 제공자 사용 (API 키 없이도 테스트 가능)
    os.environ["PROVIDER"] = "mock"
    
    try:
        labeler = AWSLLMAutoLabeler("config.yaml")
        
        # 테스트 이미지 생성 (실제로는 존재하는 이미지 사용)
        test_image_path = "images/test.png"
        if os.path.exists(test_image_path):
            result = labeler.analyze_image(test_image_path)
            print(f"🧪 테스트 결과: {len(result.detections)}개 객체 감지")
        else:
            print("⚠️ 테스트 이미지가 없습니다. 실제 이미지로 테스트하세요.")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

def main():
    """메인 함수"""
    print("🚀 AWS LLM 오토라벨러 사용 예시")
    print("=" * 50)
    
    # 예시 실행
    example_single_image()
    example_batch_analysis()
    example_custom_config()
    example_test_mode()
    
    print("\n" + "=" * 50)
    print("📚 추가 사용법:")
    print("   - CLI: python main.py --images image1.png image2.png")
    print("   - 배치: python main.py --images-dir ./images")
    print("   - 테스트: python main.py --test")
    print("   - 출력 형식: python main.py --format labelstudio")

if __name__ == "__main__":
    main()
