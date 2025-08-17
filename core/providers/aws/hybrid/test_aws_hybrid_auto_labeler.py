"""
AWS Hybrid Auto Labeler 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.providers.aws.hybrid import AWSHybridAutoLabeler


def test_aws_hybrid_auto_labeler():
    """AWS Hybrid Auto Labeler 테스트"""
    print("🧪 AWS Hybrid Auto Labeler 테스트 시작")
    
    # 설정
    config = {
        "data": {
            "icons_dir": "data/aws/icons",
            "taxonomy_csv": "data/aws/taxonomy/aws_resources_models.csv"
        },
        "cv": {
            "clip_name": "ViT-B-32",
            "clip_pretrained": "laion2b_s34b_b79k"
        },
        "llm": {
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "${OPENAI_API_KEY}",
            "vision_model": "gpt-4-vision-preview"
        },
        "detection": {
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
            "accept_score": 0.35,
            "orb_nfeatures": 500,
            "score_clip_w": 0.6,
            "score_orb_w": 0.3,
            "score_ocr_w": 0.1
        },
        "runtime": {
            "mode": "full_image",
            "conf_threshold": 0.5,
            "patch_size": 512,
            "patch_stride": 256,
            "max_tokens": 2000,
            "temperature": 0.0
        },
        "hybrid": {
            "cv_weight": 0.6,
            "llm_weight": 0.4,
            "fusion_method": "weighted",
            "iou_threshold": 0.5,
            "confidence_threshold": 0.3
        },
        "ocr": {
            "enabled": True,
            "lang": ["en"]
        }
    }
    
    try:
        # 오토라벨러 생성
        labeler = AWSHybridAutoLabeler(config)
        
        # 통계 확인
        stats = labeler.get_aws_hybrid_statistics()
        print(f"📊 하이브리드 통계: {stats}")
        
        # 지원 데이터 타입 확인
        supported_types = labeler.get_supported_data_types()
        print(f"📋 지원 데이터 타입: {supported_types}")
        
        # 설정 검증
        is_valid, errors = labeler.validate_config()
        if is_valid:
            print("✅ 설정 검증 통과")
        else:
            print(f"❌ 설정 검증 실패: {errors}")
        
        # 융합 방법 테스트
        fusion_methods = ["weighted", "ensemble", "confidence", "iou_based"]
        print(f"🔄 지원 융합 방법: {fusion_methods}")
        
        print("✅ AWS Hybrid Auto Labeler 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
    test_aws_hybrid_auto_labeler()
