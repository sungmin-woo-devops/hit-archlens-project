"""
AWS LLM Auto Labeler 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.providers.aws.llm import AWSLLMAutoLabeler


def test_aws_llm_auto_labeler():
    """AWS LLM Auto Labeler 테스트"""
    print("�� AWS LLM Auto Labeler 테스트 시작")
    
    # 설정
    config = {
        "data": {
            "taxonomy_csv": "data/aws/taxonomy/aws_resources_models.csv"
        },
        "llm": {
            "provider": "openai",  # 또는 "deepseek", "anthropic", "local"
            "base_url": "https://api.openai.com/v1",
            "api_key": "${OPENAI_API_KEY}",  # 환경변수에서 로드
            "vision_model": "gpt-4-vision-preview"
        },
        "prompt": {
            "system_prompt": "You are a precise AWS service recognizer.",
            "user_prompt_template": "Identify AWS services in this diagram."
        },
        "runtime": {
            "mode": "full_image",  # "full_image", "patch", "hybrid"
            "conf_threshold": 0.5,
            "patch_size": 512,
            "patch_stride": 256,
            "max_tokens": 2000,
            "temperature": 0.0
        }
    }
    
    try:
        # 오토라벨러 생성
        labeler = AWSLLMAutoLabeler(config)
        
        # 통계 확인
        stats = labeler.get_aws_llm_statistics()
        print(f"�� LLM 통계: {stats}")
        
        # 지원 데이터 타입 확인
        supported_types = labeler.get_supported_data_types()
        print(f"📋 지원 데이터 타입: {supported_types}")
        
        # 설정 검증
        is_valid, errors = labeler.validate_config()
        if is_valid:
            print("✅ 설정 검증 통과")
        else:
            print(f"❌ 설정 검증 실패: {errors}")
        
        print("✅ AWS LLM Auto Labeler 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
    test_aws_llm_auto_labeler()
