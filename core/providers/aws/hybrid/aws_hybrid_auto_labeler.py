"""
AWS Hybrid Auto Labeler Implementation

AWS 전용 하이브리드 오토라벨러 구현체
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from PIL import Image

# core 프레임워크 import
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))
from core.auto_labeler.hybrid_auto_labeler import HybridAutoLabeler
from core.providers.aws.cv import AWSCVAutoLabeler
from core.providers.aws.llm import AWSLLMAutoLabeler
from core.models import (
    DetectionResult, 
    AnalysisResult,
    CloudProvider,
    AnalysisMethod
)


class AWSHybridAutoLabeler(HybridAutoLabeler):
    """
    AWS 전용 하이브리드 오토라벨러
    
    CV와 LLM을 결합한 AWS 서비스 아이콘 인식 시스템
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        AWS 하이브리드 오토라벨러 초기화
        
        Args:
            config: AWS 전용 설정
        """
        # AWS 기본 설정 적용
        aws_config = self._prepare_aws_config(config)
        
        # 먼저 CV와 LLM 오토라벨러를 생성
        self.cv_labeler = self._create_cv_labeler(CloudProvider.AWS, aws_config)
        self.llm_labeler = self._create_llm_labeler(CloudProvider.AWS, aws_config)
        
        # 그 다음 부모 클래스 초기화
        super().__init__(CloudProvider.AWS, aws_config)
        
        # AWS 특화 컴포넌트 초기화
        self._setup_aws_specific_components()
        
        print(f"   - AWS 하이브리드 오토라벨러 초기화 완료")
    
    def _prepare_aws_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """AWS 전용 설정 준비"""
        # 기본 AWS 설정
        aws_config = {
            "cloud_provider": "aws",
            "method": "hybrid",
            "data": {
                "icons_dir": config.get("data", {}).get("icons_dir", "./icons"),
                "taxonomy_csv": config.get("data", {}).get("taxonomy_csv", "./aws_resources_models.csv")
            },
            "cv": {
                "clip_name": config.get("cv", {}).get("clip_name", "ViT-B-32"),
                "clip_pretrained": config.get("cv", {}).get("clip_pretrained", "laion2b_s34b_b79k")
            },
            "llm": {
                "provider": config.get("llm", {}).get("provider", "openai"),
                "base_url": config.get("llm", {}).get("base_url"),
                "api_key": config.get("llm", {}).get("api_key"),
                "vision_model": config.get("llm", {}).get("vision_model", "gpt-4-vision-preview")
            },
            "detection": {
                "max_size": config.get("detection", {}).get("max_size", 1600),
                "canny_low": config.get("detection", {}).get("canny_low", 60),
                "canny_high": config.get("detection", {}).get("canny_high", 160),
                "mser_delta": config.get("detection", {}).get("mser_delta", 5),
                "min_area": config.get("detection", {}).get("min_area", 900),
                "max_area": config.get("detection", {}).get("max_area", 90000),
                "win": config.get("detection", {}).get("win", 128),
                "stride": config.get("detection", {}).get("stride", 96),
                "iou_nms": config.get("detection", {}).get("iou_nms", 0.45)
            },
            "retrieval": {
                "topk": config.get("retrieval", {}).get("topk", 5),
                "accept_score": config.get("retrieval", {}).get("accept_score", 0.35),
                "orb_nfeatures": config.get("retrieval", {}).get("orb_nfeatures", 500),
                "score_clip_w": config.get("retrieval", {}).get("score_clip_w", 0.6),
                "score_orb_w": config.get("retrieval", {}).get("score_orb_w", 0.3),
                "score_ocr_w": config.get("retrieval", {}).get("score_ocr_w", 0.1)
            },
            "runtime": {
                "mode": config.get("runtime", {}).get("mode", "full_image"),
                "conf_threshold": config.get("runtime", {}).get("conf_threshold", 0.5),
                "patch_size": config.get("runtime", {}).get("patch_size", 512),
                "patch_stride": config.get("runtime", {}).get("patch_stride", 256),
                "max_tokens": config.get("runtime", {}).get("max_tokens", 2000),
                "temperature": config.get("runtime", {}).get("temperature", 0.0)
            },
            "hybrid": {
                "cv_weight": config.get("hybrid", {}).get("cv_weight", 0.6),
                "llm_weight": config.get("hybrid", {}).get("llm_weight", 0.4),
                "fusion_method": config.get("hybrid", {}).get("fusion_method", "weighted"),
                "iou_threshold": config.get("hybrid", {}).get("iou_threshold", 0.5),
                "confidence_threshold": config.get("hybrid", {}).get("confidence_threshold", 0.3)
            },
            "ocr": {
                "enabled": config.get("ocr", {}).get("enabled", True),
                "lang": config.get("ocr", {}).get("lang", ["en"])
            }
        }
        
        return aws_config
    
    def _create_cv_labeler(self, cloud_provider: Union[CloudProvider, str], 
                          config: Dict[str, Any]) -> AWSCVAutoLabeler:
        """CV 오토라벨러 생성"""
        return AWSCVAutoLabeler(config)
    
    def _create_llm_labeler(self, cloud_provider: Union[CloudProvider, str], 
                           config: Dict[str, Any]) -> AWSLLMAutoLabeler:
        """LLM 오토라벨러 생성"""
        return AWSLLMAutoLabeler(config)
    
    def _setup_aws_specific_components(self):
        """AWS 특화 컴포넌트 설정"""
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
    
    def _load_taxonomy(self):
        """택소노미 로드 (오버라이드)"""
        # CV 오토라벨러의 택소노미 사용
        if hasattr(self, 'cv_labeler') and self.cv_labeler:
            return self.cv_labeler.taxonomy
        return None
    
    def get_method_name(self) -> str:
        """분석 방법 이름"""
        return "hybrid"
    
    def analyze_image(self, image_path: Union[str, Path]) -> AnalysisResult:
        """
        이미지 분석 (AWS 특화)
        
        Args:
            image_path: 분석할 이미지 경로
            
        Returns:
            AnalysisResult: 분석 결과
        """
        return super().analyze_image(image_path)
    
    def analyze_batch(self, image_paths: List[Union[str, Path]]) -> 'BatchAnalysisResult':
        """
        배치 이미지 분석 (AWS 특화)
        
        Args:
            image_paths: 분석할 이미지 경로 리스트
            
        Returns:
            BatchAnalysisResult: 배치 분석 결과
        """
        return super().analyze_batch(image_paths)
