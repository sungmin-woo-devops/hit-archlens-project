"""
AWS LLM Auto Labeler Implementation

AWS 전용 Large Language Model 기반 오토라벨러 구현체
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from PIL import Image

# core 프레임워크 import
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../'))
from core.auto_labeler.llm_auto_labeler import LLMAutoLabeler
from core.auto_labeler.llm_providers import (
    LLMProvider, 
    OpenAIProvider, 
    DeepSeekProvider,
    AnthropicProvider,
    LocalLLMProvider
)
from core.models import (
    DetectionResult, 
    BoundingBox,
    CloudProvider,
    DetectionStatus
)
from core.taxonomy import AWSTaxonomy


class AWSPromptManager:
    """AWS 전용 프롬프트 관리자"""
    
    def __init__(self):
        self.full_image_prompt = self._get_full_image_prompt()
        self.patch_prompt = self._get_patch_prompt()
    
    def _get_full_image_prompt(self) -> str:
        """전체 이미지 분석 프롬프트"""
        return """Analyze this AWS architecture diagram and identify all AWS services present.

Return a JSON array of objects with the following structure:
{
  "objects": [
    {
      "name": "service name (e.g., Amazon EC2, Amazon S3)",
      "bbox": [x, y, width, height],
      "confidence": 0.95
    }
  ]
}

Guidelines:
- Use official AWS service names (e.g., "Amazon EC2" not "EC2")
- Provide bounding boxes for each service icon
- Set confidence between 0.0 and 1.0
- Only include services you are confident about
- Return valid JSON only"""
    
    def _get_patch_prompt(self) -> str:
        """패치 분석 프롬프트"""
        return """Analyze this image patch and identify any AWS services present.

Return a JSON array of objects with the following structure:
{
  "objects": [
    {
      "name": "service name (e.g., Amazon EC2, Amazon S3)",
      "bbox": [x, y, width, height],
      "confidence": 0.95
    }
  ]
}

Guidelines:
- Use official AWS service names
- Provide bounding boxes relative to this patch
- Set confidence between 0.0 and 1.0
- Only include services you are confident about
- Return valid JSON only"""
    
    def get_full_image_prompt(self) -> str:
        """전체 이미지 프롬프트 반환"""
        return self.full_image_prompt
    
    def get_patch_prompt(self) -> str:
        """패치 프롬프트 반환"""
        return self.patch_prompt


class AWSLLMAutoLabeler(LLMAutoLabeler):
    """
    AWS 전용 LLM 기반 오토라벨러
    
    다양한 LLM 제공자를 지원하며 AWS 서비스 인식에 최적화됨
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        AWS LLM 오토라벨러 초기화
        
        Args:
            config: AWS 전용 설정
        """
        # AWS 기본 설정 적용
        aws_config = self._prepare_aws_config(config)
        
        # config를 인스턴스 변수로 저장
        self.config = aws_config
        
        # AWS 특화 컴포넌트 초기화
        self._setup_aws_specific_components()
        
        # 그 다음 부모 클래스 초기화
        super().__init__(CloudProvider.AWS, aws_config)
        
        print(f"   - LLM 제공자: {config.get('llm', {}).get('provider', 'Not set')}")
        print(f"   - 분석 모드: {config.get('runtime', {}).get('mode', 'Not set')}")
    
    def _prepare_aws_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """AWS 전용 설정 준비"""
        # 기본 AWS 설정
        aws_config = {
            "cloud_provider": "aws",
            "method": "llm",
            "data": {
                "taxonomy_csv": config.get("data", {}).get("taxonomy_csv", "./aws_resources_models.csv")
            },
            "llm": {
                "provider": config.get("llm", {}).get("provider", "openai"),
                "base_url": config.get("llm", {}).get("base_url"),
                "api_key": config.get("llm", {}).get("api_key"),
                "vision_model": config.get("llm", {}).get("vision_model", "gpt-4-vision-preview")
            },
            "prompt": {
                "system_prompt": config.get("prompt", {}).get("system_prompt", ""),
                "user_prompt_template": config.get("prompt", {}).get("user_prompt_template", "")
            },
            "runtime": {
                "mode": config.get("runtime", {}).get("mode", "full_image"),
                "conf_threshold": config.get("runtime", {}).get("conf_threshold", 0.5),
                "patch_size": config.get("runtime", {}).get("patch_size", 512),
                "patch_stride": config.get("runtime", {}).get("patch_stride", 256),
                "max_tokens": config.get("runtime", {}).get("max_tokens", 2000),
                "temperature": config.get("runtime", {}).get("temperature", 0.0)
            }
        }
        
        return aws_config
    
    def _setup_llm_components(self):
        """LLM 컴포넌트 설정"""
        # 프롬프트 관리자 초기화
        self.prompt_manager = AWSPromptManager()
        
        # LLM 제공자 설정
        self.llm_provider = self._setup_llm_provider()
    
    def _setup_aws_specific_components(self):
        """AWS 특화 컴포넌트 설정"""
        # AWS 택소노미 로드
        self.aws_taxonomy = self._load_aws_taxonomy_internal()
        
        # 프롬프트 관리자 초기화
        self.prompt_manager = AWSPromptManager()
        
        # AWS 서비스 코드 매핑
        self.service_code_mapping = {
            "Amazon EC2": "ec2",
            "Amazon S3": "s3", 
            "AWS Lambda": "lambda",
            "Amazon RDS": "rds",
            "Amazon DynamoDB": "dynamodb",
            "Amazon CloudFront": "cloudfront",
            "Amazon API Gateway": "apigateway",
            "Amazon SNS": "sns",
            "Amazon SQS": "sqs",
            "Amazon CloudWatch": "cloudwatch",
            "AWS IAM": "iam",
            "Amazon VPC": "vpc",
            "Elastic Load Balancing": "elb",
            "Auto Scaling": "autoscaling",
            "Amazon ECS": "ecs",
            "Amazon EKS": "eks"
        }
    
    def _setup_llm_provider(self) -> LLMProvider:
        """LLM 제공자 설정"""
        provider_name = self.llm_config.get("provider", "openai")
        base_url = self.llm_config.get("base_url")
        api_key = self.llm_config.get("api_key")
        vision_model = self.llm_config.get("vision_model")
        
        if not api_key:
            raise ValueError(f"{provider_name} API 키가 설정되지 않았습니다")
        
        if provider_name == "openai":
            return OpenAIProvider(
                base_url=base_url or "https://api.openai.com/v1",
                api_key=api_key,
                vision_model=vision_model or "gpt-4-vision-preview"
            )
        elif provider_name == "deepseek":
            return DeepSeekProvider(
                base_url=base_url or "https://api.deepseek.com",
                api_key=api_key,
                vision_model=vision_model or "deepseek-vision"
            )
        elif provider_name == "anthropic":
            return AnthropicProvider(
                base_url=base_url or "https://api.anthropic.com",
                api_key=api_key,
                vision_model=vision_model or "claude-3-sonnet-20240229"
            )
        elif provider_name == "local":
            return LocalLLMProvider(
                base_url=base_url or "http://localhost:1234/v1",
                api_key=api_key,
                vision_model=vision_model or "local-vision-model"
            )
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {provider_name}")
    
    def _load_aws_taxonomy_internal(self) -> Optional[AWSTaxonomy]:
        """AWS 택소노미 로드 (내부 호출용)"""
        try:
            taxonomy_path = self.config.get("data", {}).get("taxonomy_csv")
            if not taxonomy_path or not os.path.exists(taxonomy_path):
                print(f"⚠️ AWS 택소노미 파일을 찾을 수 없습니다: {taxonomy_path}")
                return None
            
            taxonomy = AWSTaxonomy()
            success = taxonomy.load_from_source(taxonomy_path)
            
            if success:
                print(f"✅ AWS 택소노미 로드 완료: {len(taxonomy.get_all_names())}개 서비스")
                return taxonomy
            else:
                print("❌ AWS 택소노미 로드 실패")
                return None
            
        except Exception as e:
            print(f"❌ AWS 택소노미 로드 실패: {e}")
            return None
    
    def _generate_prompt(self, image: Image.Image, mode: str = "full") -> str:
        """프롬프트 생성"""
        if mode == "full":
            return self.prompt_manager.get_full_image_prompt()
        else:
            return self.prompt_manager.get_patch_prompt()
    
    def _get_llm_provider(self):
        """LLM 제공자 반환"""
        return self.llm_provider
    
    def _load_taxonomy(self):
        """택소노미 로드 (오버라이드)"""
        if hasattr(self, 'aws_taxonomy'):
            return self.aws_taxonomy
        return None
    
    def get_aws_llm_statistics(self) -> Dict[str, Any]:
        """
        AWS LLM 특화 통계 정보
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        return {
            **self.get_llm_statistics(),
            "aws_taxonomy_loaded": self.aws_taxonomy is not None,
            "service_code_mapping_count": len(self.service_code_mapping)
        }
