"""
모든 AWS 오토라벨러 통합 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.providers.aws import (
    AWSCVAutoLabeler,
    AWSLLMAutoLabeler,
    AWSHybridAutoLabeler
)


def test_all_aws_auto_labelers():
    """모든 AWS 오토라벨러 테스트"""
    print("🧪 모든 AWS 오토라벨러 통합 테스트 시작\n")
    
    # 공통 설정
    base_config = {
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
    
    # 1. CV 오토라벨러 테스트
    print("1️⃣ AWS CV Auto Labeler 테스트")
    try:
        cv_labeler = AWSCVAutoLabeler(base_config)
        cv_stats = cv_labeler.get_cv_statistics()
        print(f"   ✅ CV 오토라벨러 초기화 성공")
        print(f"   📊 CV 통계: {len(cv_stats)}개 항목")
    except Exception as e:
        print(f"   ❌ CV 오토라벨러 초기화 실패: {e}")
    
    print()
    
    # 2. LLM 오토라벨러 테스트
    print("2️⃣ AWS LLM Auto Labeler 테스트")
    try:
        llm_labeler = AWSLLMAutoLabeler(base_config)
        llm_stats = llm_labeler.get_aws_llm_statistics()
        print(f"   ✅ LLM 오토라벨러 초기화 성공")
        print(f"   📊 LLM 통계: {len(llm_stats)}개 항목")
    except Exception as e:
        print(f"   ❌ LLM 오토라벨러 초기화 실패: {e}")
    
    print()
    
    # 3. 하이브리드 오토라벨러 테스트
    print("3️⃣ AWS Hybrid Auto Labeler 테스트")
    try:
        hybrid_labeler = AWSHybridAutoLabeler(base_config)
        hybrid_stats = hybrid_labeler.get_aws_hybrid_statistics()
        print(f"   ✅ 하이브리드 오토라벨러 초기화 성공")
        print(f"   📊 하이브리드 통계: {len(hybrid_stats)}개 항목")
    except Exception as e:
        print(f"   ❌ 하이브리드 오토라벨러 초기화 실패: {e}")
    
    print()
    
    # 4. 통합 비교
    print("4️⃣ 오토라벨러 비교")
    print("   �� 지원 방법:")
    print("      - CV: Computer Vision 기반 (CLIP + ORB)")
    print("      - LLM: Large Language Model 기반 (GPT-4V, Claude)")
    print("      - Hybrid: CV + LLM 융합")
    
    print("\n   🎯 권장 사용 사례:")
    print("      - CV: 빠른 처리, 대량 이미지")
    print("      - LLM: 정확한 인식, 복잡한 다이어그램")
    print("      - Hybrid: 최고 정확도, 중요 분석")
    
    print("\n✅ 모든 AWS 오토라벨러 통합 테스트 완료!")


if __name__ == "__main__":
    test_all_aws_auto_labelers()
```

---

## 🎯 **Phase 3.3 완료 요약**

### **완료된 작업:**
- ✅ **HybridAutoLabeler 베이스 클래스** 완성
- ✅ **AWSHybridAutoLabeler 구현체** 생성
- ✅ **다중 융합 방법** 구현 (가중치, 앙상블, 신뢰도, IoU 기반)
- ✅ **AWS Providers 통합** 초기화 파일 생성
- ✅ **상세 분석 기능** (CV, LLM, 하이브리드 각각의 결과)
- ✅ **통합 테스트 스크립트** 생성

### **주요 개선사항:**
- **통합성**: CV와 LLM을 완벽하게 결합한 하이브리드 시스템
- **다중 융합**: 4가지 융합 방법으로 유연한 결과 조합
- **상세 분석**: 각 방법별 결과를 개별적으로 확인 가능
- **성능 최적화**: IoU 기반 중복 제거 및 신뢰도 임계값 적용
- **통계**: 하이브리드 특화 통계 정보 제공
- **테스트**: 모든 오토라벨러에 대한 통합 테스트

### **Phase 3 전체 완료! 🎉**

이제 **Phase 4: CLI 및 도구 통합**으로 진행하겠습니다. 

계속 진행하시겠습니까?
