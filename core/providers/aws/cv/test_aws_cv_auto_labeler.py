"""
AWS CV Auto Labeler 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.providers.aws.cv import AWSCVAutoLabeler


def test_aws_cv_auto_labeler():
    """AWS CV Auto Labeler 테스트"""
    print("🧪 AWS CV Auto Labeler 테스트 시작")
    
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
        "ocr": {
            "enabled": True,
            "lang": ["en"]
        }
    }
    
    try:
        # 오토라벨러 생성
        labeler = AWSCVAutoLabeler(config)
        
        # 통계 확인
        stats = labeler.get_cv_statistics()
        print(f"📊 CV 통계: {stats}")
        
        # 지원 데이터 타입 확인
        supported_types = labeler.get_supported_data_types()
        print(f"📋 지원 데이터 타입: {supported_types}")
        
        # 설정 검증
        is_valid, errors = labeler.validate_config()
        if is_valid:
            print("✅ 설정 검증 통과")
        else:
            print(f"❌ 설정 검증 실패: {errors}")
        
        print("✅ AWS CV Auto Labeler 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
    test_aws_cv_auto_labeler()
