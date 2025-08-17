"""
설정 검증 도구

설정 파일의 유효성을 검증하고 기본값을 제공합니다.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple


class ConfigValidator:
    """설정 검증기"""
    
    def __init__(self):
        self.required_fields = {
            "data": ["icons_dir", "taxonomy_csv"],
            "cv": ["clip_name", "clip_pretrained"],
            "llm": ["provider", "api_key", "vision_model"],
            "detection": ["max_size", "min_area", "max_area"],
            "retrieval": ["topk", "accept_score"],
            "runtime": ["mode", "conf_threshold"],
            "hybrid": ["cv_weight", "llm_weight", "fusion_method"]
        }
        
        self.valid_values = {
            "llm.provider": ["openai", "deepseek", "anthropic", "local"],
            "runtime.mode": ["full_image", "patch", "hybrid"],
            "hybrid.fusion_method": ["weighted", "ensemble", "confidence", "iou_based"]
        }
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        설정 유효성 검증
        
        Args:
            config: 검증할 설정
            
        Returns:
            Tuple[bool, List[str]]: (유효성 여부, 오류 메시지 목록)
        """
        errors = []
        
        # 필수 필드 검증
        for section, fields in self.required_fields.items():
            if section not in config:
                errors.append(f"필수 섹션이 없습니다: {section}")
                continue
            
            for field in fields:
                if field not in config[section]:
                    errors.append(f"필수 필드가 없습니다: {section}.{field}")
        
        # 값 유효성 검증
        for path, valid_values in self.valid_values.items():
            value = self._get_nested_value(config, path)
            if value is not None and value not in valid_values:
                errors.append(f"유효하지 않은 값: {path} = {value} (유효값: {valid_values})")
        
        # 경로 유효성 검증
        path_errors = self._validate_paths(config)
        errors.extend(path_errors)
        
        # 환경변수 검증
        env_errors = self._validate_environment(config)
        errors.extend(env_errors)
        
        return len(errors) == 0, errors
    
    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """중첩된 경로에서 값 가져오기"""
        keys = path.split('.')
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _validate_paths(self, config: Dict[str, Any]) -> List[str]:
        """경로 유효성 검증"""
        errors = []
        
        # 데이터 디렉터리 검증
        if "data" in config:
            data_config = config["data"]
            
            # 아이콘 디렉터리
            icons_dir = data_config.get("icons_dir")
            if icons_dir and not Path(icons_dir).exists():
                errors.append(f"아이콘 디렉터리가 존재하지 않습니다: {icons_dir}")
            
            # 택소노미 파일
            taxonomy_csv = data_config.get("taxonomy_csv")
            if taxonomy_csv and not Path(taxonomy_csv).exists():
                errors.append(f"택소노미 파일이 존재하지 않습니다: {taxonomy_csv}")
        
        return errors
    
    def _validate_environment(self, config: Dict[str, Any]) -> List[str]:
        """환경변수 검증"""
        errors = []
        
        # LLM API 키 검증
        if "llm" in config:
            llm_config = config["llm"]
            api_key = llm_config.get("api_key", "")
            
            if api_key.startswith("${") and api_key.endswith("}"):
                env_var = api_key[2:-1]
                if not os.getenv(env_var):
                    errors.append(f"환경변수가 설정되지 않았습니다: {env_var}")
        
        return errors
    
    def get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "data": {
                "icons_dir": "data/aws/icons",
                "taxonomy_csv": "data/aws/taxonomy/aws_resources_models.csv",
                "images_dir": "images",
                "output_dir": "output"
            },
            "cv": {
                "clip_name": "ViT-B-32",
                "clip_pretrained": "laion2b_s34b_b79k",
                "device": "auto"
            },
            "llm": {
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "${OPENAI_API_KEY}",
                "vision_model": "gpt-4-vision-preview",
                "timeout": 120,
                "max_retries": 3
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
                "iou_nms": 0.45,
                "use_canny": True,
                "use_mser": True,
                "use_sliding_window": True
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
                "temperature": 0.0,
                "batch_size": 1
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
                "lang": ["en"],
                "confidence_threshold": 0.5
            },
            "collectors": {
                "icons": {
                    "zip_path": "Asset-Package.zip",
                    "output_dir": "data/aws/icons"
                },
                "services": {
                    "output_dir": "data/aws/services"
                },
                "products": {
                    "api_url": "https://aws.amazon.com/api/dirs/items/search?item.directoryId=aws-products&sort_by=item.additionalFields.productNameLowercase&size=1000&language=en&item.locale=en_US",
                    "output_dir": "data/aws/products",
                    "timeout": 30
                }
            },
            "aws": {
                "region": "us-east-1",
                "max_retries": 3,
                "timeout": 30
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/hit_archlens.log"
            },
            "performance": {
                "parallel_processing": True,
                "max_workers": 4,
                "memory_limit": "4GB",
                "cache_enabled": True,
                "cache_dir": "cache"
            }
        }
    
    def create_config_file(self, output_path: str, template: str = "default") -> bool:
        """
        설정 파일 생성
        
        Args:
            output_path: 출력 파일 경로
            template: 템플릿 이름
            
        Returns:
            bool: 생성 성공 여부
        """
        try:
            config = self.get_default_config()
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ 설정 파일 생성 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 설정 파일 생성 실패: {e}")
            return False


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="설정 검증 도구")
    parser.add_argument("--validate", "-v", help="검증할 설정 파일")
    parser.add_argument("--create", "-c", help="생성할 설정 파일")
    parser.add_argument("--template", "-t", default="default", help="템플릿 이름")
    
    args = parser.parse_args()
    
    validator = ConfigValidator()
    
    if args.validate:
        # 설정 검증
        try:
            with open(args.validate, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            is_valid, errors = validator.validate_config(config)
            
            if is_valid:
                print("✅ 설정 파일이 유효합니다")
            else:
                print("❌ 설정 파일에 오류가 있습니다:")
                for error in errors:
                    print(f"   - {error}")
                    
        except Exception as e:
            print(f"❌ 설정 파일 로드 실패: {e}")
    
    elif args.create:
        # 설정 파일 생성
        validator.create_config_file(args.create, args.template)
    
    else:
        # 기본 설정 출력
        config = validator.get_default_config()
        print(yaml.dump(config, default_flow_style=False, allow_unicode=True))


if __name__ == "__main__":
    main()
