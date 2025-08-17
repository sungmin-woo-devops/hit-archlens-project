"""
Unified Taxonomy Generator

수집된 AWS 데이터를 정규화하여 통합 카테고리 CSV 파일을 생성
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..models import AWSServiceInfo, AWSServiceIcon


class UnifiedTaxonomyGenerator:
    """
    통합 택소노미 생성기
    
    수집된 아이콘, 서비스, 제품 정보를 통합하여
    정규화된 카테고리 CSV 파일을 생성
    """
    
    def __init__(self, data_dir: str = "out"):
        """
        초기화
        
        Args:
            data_dir: 데이터 디렉터리 경로
        """
        self.data_dir = Path(data_dir)
        self.aws_dir = self.data_dir / "aws"
        
        # 출력 디렉터리
        self.unified_dir = self.data_dir / "unified"
        self.unified_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ 통합 택소노미 생성기 초기화 완료")
        print(f"   - 데이터 디렉터리: {self.data_dir}")
        print(f"   - 통합 출력 디렉터리: {self.unified_dir}")
    
    def generate_unified_taxonomy(self) -> bool:
        """
        통합 택소노미 생성
        
        Returns:
            bool: 생성 성공 여부
        """
        try:
            print("🔍 통합 택소노미 생성 시작")
            
            # 1. 아이콘 데이터 로드
            icon_data = self._load_icon_data()
            print(f"   �� 아이콘 데이터: {len(icon_data)}개")
            
            # 2. 서비스 데이터 로드
            service_data = self._load_service_data()
            print(f"   📊 서비스 데이터: {len(service_data)}개")
            
            # 3. 제품 데이터 로드
            product_data = self._load_product_data()
            print(f"   📊 제품 데이터: {len(product_data)}개")
            
            # 4. 기존 택소노미 데이터 로드
            taxonomy_data = self._load_taxonomy_data()
            print(f"   �� 택소노미 데이터: {len(taxonomy_data)}개")
            
            # 5. 데이터 통합 및 정규화
            unified_data = self._merge_and_normalize_data(
                icon_data, service_data, product_data, taxonomy_data
            )
            print(f"   📊 통합 데이터: {len(unified_data)}개")
            
            # 6. 통합 CSV 파일 생성
            csv_path = self.unified_dir / "aws_unified_taxonomy.csv"
            self._save_unified_csv(unified_data, csv_path)
            
            # 7. 통합 JSON 파일 생성
            json_path = self.unified_dir / "aws_unified_taxonomy.json"
            self._save_unified_json(unified_data, json_path)
            
            # 8. 통계 리포트 생성
            stats_path = self.unified_dir / "unification_stats.json"
            self._save_unification_stats(
                len(icon_data), len(service_data), len(product_data), 
                len(taxonomy_data), len(unified_data), stats_path
            )
            
            print(f"✅ 통합 택소노미 생성 완료")
            print(f"   - CSV 파일: {csv_path}")
            print(f"   - JSON 파일: {json_path}")
            print(f"   - 통계 파일: {stats_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ 통합 택소노미 생성 실패: {e}")
            return False
    
    def _load_icon_data(self) -> List[Dict[str, Any]]:
        """아이콘 데이터 로드"""
        icon_data = []
        
        # CSV 파일 로드
        csv_path = self.aws_dir / "icons" / "aws_icons_mapping.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                icon_data.append({
                    "type": "icon",
                    "group": row.get("group", ""),
                    "service": row.get("service", ""),
                    "zip_path": row.get("zip_path", ""),
                    "category": row.get("category", ""),
                    "file_path": row.get("file_path", ""),
                    "source": "icon_mapping"
                })
        
        # JSON 파일 로드
        json_path = self.aws_dir / "icons" / "aws_icons_mapping.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                for item in json_data:
                    if not any(d["service"] == item.get("service", "") for d in icon_data):
                        icon_data.append({
                            "type": "icon",
                            "group": item.get("group", ""),
                            "service": item.get("service", ""),
                            "zip_path": item.get("zip_path", ""),
                            "category": item.get("category", ""),
                            "file_path": item.get("file_path", ""),
                            "source": "icon_mapping"
                        })
        
        return icon_data
    
    def _load_service_data(self) -> List[Dict[str, Any]]:
        """서비스 데이터 로드"""
        service_data = []
        
        # CSV 파일 로드
        csv_path = self.aws_dir / "services" / "aws_services.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                service_data.append({
                    "type": "service",
                    "service_code": row.get("service_code", ""),
                    "service_name": row.get("service_name", ""),
                    "regions": row.get("regions", ""),
                    "main_resource_example": row.get("main_resource_example", ""),
                    "source": "boto3_metadata"
                })
        
        # JSON 파일 로드
        json_path = self.aws_dir / "services" / "aws_services.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                for item in json_data:
                    if not any(d["service_code"] == item.get("service_code", "") for d in service_data):
                        service_data.append({
                            "type": "service",
                            "service_code": item.get("service_code", ""),
                            "service_name": item.get("service_name", ""),
                            "regions": item.get("regions", ""),
                            "main_resource_example": item.get("main_resource_example", ""),
                            "source": "boto3_metadata"
                        })
        
        return service_data
    
    def _load_product_data(self) -> List[Dict[str, Any]]:
        """제품 데이터 로드"""
        product_data = []
        
        # CSV 파일 로드
        csv_path = self.aws_dir / "products" / "aws_products.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                product_data.append({
                    "type": "product",
                    "product_name": row.get("product_name", ""),
                    "product_category": row.get("product_category", ""),
                    "description": row.get("description", ""),
                    "source": "aws_api"
                })
        
        # JSON 파일 로드
        json_path = self.aws_dir / "products" / "aws_products.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                for item in json_data:
                    if not any(d.get("product_name") == item.get("product_name", "") for d in product_data):
                        product_data.append({
                            "type": "product",
                            "product_name": item.get("product_name", ""),
                            "product_category": item.get("product_category", ""),
                            "description": item.get("description", ""),
                            "source": "aws_api"
                        })
        
        return product_data
    
    def _load_taxonomy_data(self) -> List[Dict[str, Any]]:
        """기존 택소노미 데이터 로드"""
        taxonomy_data = []
        
        # 기존 택소노미 파일들 로드
        taxonomy_files = [
            self.data_dir / "aws_resources_models.csv",
            self.aws_dir / "taxonomy" / "aws_resources_models.csv",
            self.aws_dir / "taxonomy" / "aws_resources_models_cv.csv",
            self.aws_dir / "taxonomy" / "aws_resources_models_out.csv"
        ]
        
        for file_path in taxonomy_files:
            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    for _, row in df.iterrows():
                        taxonomy_data.append({
                            "type": "taxonomy",
                            "service_code": row.get("service_code", ""),
                            "service_full_name": row.get("service_full_name", ""),
                            "main_resource_example": row.get("main_resource_example", ""),
                            "secondary_examples": row.get("secondary_examples", ""),
                            "from_operation": row.get("from_operation", ""),
                            "id_fields_seen": row.get("id_fields_seen", ""),
                            "source": file_path.name
                        })
                except Exception as e:
                    print(f"⚠️ 택소노미 파일 로드 실패: {file_path} - {e}")
        
        return taxonomy_data
    
    def _merge_and_normalize_data(self, icon_data: List[Dict], service_data: List[Dict], 
                                 product_data: List[Dict], taxonomy_data: List[Dict]) -> List[Dict]:
        """데이터 통합 및 정규화"""
        unified_data = []
        
        # 서비스 코드 매핑
        service_mapping = {}
        for service in service_data:
            service_code = service.get("service_code", "").lower()
            service_name = service.get("service_name", "")
            if service_code:
                service_mapping[service_code] = service_name
                service_mapping[service_name.lower()] = service_name
        
        # 아이콘 데이터 정규화
        for icon in icon_data:
            service_name = icon.get("service", "")
            normalized_service = self._normalize_service_name(service_name, service_mapping)
            
            unified_data.append({
                "canonical_service_name": normalized_service,
                "original_service_name": service_name,
                "service_code": self._extract_service_code(normalized_service),
                "group": icon.get("group", ""),
                "category": icon.get("category", ""),
                "type": "icon",
                "source": icon.get("source", ""),
                "file_path": icon.get("file_path", ""),
                "zip_path": icon.get("zip_path", ""),
                "confidence": 1.0,
                "normalization_method": "icon_mapping"
            })
        
        # 서비스 데이터 정규화
        for service in service_data:
            service_name = service.get("service_name", "")
            service_code = service.get("service_code", "")
            
            unified_data.append({
                "canonical_service_name": service_name,
                "original_service_name": service_name,
                "service_code": service_code,
                "group": self._categorize_service(service_name),
                "category": self._categorize_service(service_name),
                "type": "service",
                "source": service.get("source", ""),
                "regions": service.get("regions", ""),
                "main_resource_example": service.get("main_resource_example", ""),
                "confidence": 1.0,
                "normalization_method": "boto3_metadata"
            })
        
        # 택소노미 데이터 정규화
        for taxonomy in taxonomy_data:
            service_name = taxonomy.get("service_full_name", "")
            service_code = taxonomy.get("service_code", "")
            
            if service_name and not any(d["canonical_service_name"] == service_name for d in unified_data):
                unified_data.append({
                    "canonical_service_name": service_name,
                    "original_service_name": service_name,
                    "service_code": service_code,
                    "group": self._categorize_service(service_name),
                    "category": self._categorize_service(service_name),
                    "type": "taxonomy",
                    "source": taxonomy.get("source", ""),
                    "main_resource_example": taxonomy.get("main_resource_example", ""),
                    "secondary_examples": taxonomy.get("secondary_examples", ""),
                    "confidence": 0.9,
                    "normalization_method": "taxonomy_mapping"
                })
        
        # 중복 제거 및 정렬
        unique_data = []
        seen_services = set()
        
        for item in unified_data:
            canonical_name = item["canonical_service_name"]
            if canonical_name and canonical_name not in seen_services:
                unique_data.append(item)
                seen_services.add(canonical_name)
        
        # 신뢰도 순으로 정렬
        unique_data.sort(key=lambda x: x["confidence"], reverse=True)
        
        return unique_data
    
    def _normalize_service_name(self, service_name: str, service_mapping: Dict[str, str]) -> str:
        """서비스명 정규화"""
        if not service_name:
            return ""
        
        # 매핑에서 찾기
        normalized = service_mapping.get(service_name.lower(), service_name)
        
        # 일반적인 패턴 정규화
        normalized = normalized.replace("Amazon ", "").replace("AWS ", "")
        normalized = normalized.strip()
        
        return normalized
    
    def _extract_service_code(self, service_name: str) -> str:
        """서비스명에서 서비스 코드 추출"""
        if not service_name:
            return ""
        
        # 일반적인 패턴들
        code_mapping = {
            "EC2": "ec2",
            "S3": "s3",
            "Lambda": "lambda",
            "RDS": "rds",
            "DynamoDB": "dynamodb",
            "CloudFront": "cloudfront",
            "API Gateway": "apigateway",
            "SNS": "sns",
            "SQS": "sqs",
            "CloudWatch": "cloudwatch",
            "IAM": "iam",
            "VPC": "vpc",
            "Elastic Load Balancing": "elb",
            "Auto Scaling": "autoscaling",
            "ECS": "ecs",
            "EKS": "eks"
        }
        
        for key, value in code_mapping.items():
            if key.lower() in service_name.lower():
                return value
        
        return service_name.lower().replace(" ", "")
    
    def _categorize_service(self, service_name: str) -> str:
        """서비스 카테고리 분류"""
        if not service_name:
            return "Unknown"
        
        service_name_lower = service_name.lower()
        
        categories = {
            "Compute": ["ec2", "lambda", "ecs", "eks", "fargate", "batch", "lightsail"],
            "Storage": ["s3", "ebs", "efs", "fsx", "storage gateway"],
            "Database": ["rds", "dynamodb", "redshift", "elasticache", "neptune"],
            "Networking": ["vpc", "cloudfront", "route 53", "api gateway", "direct connect"],
            "Security": ["iam", "cognito", "kms", "secrets manager", "guardduty"],
            "Management": ["cloudwatch", "cloudtrail", "config", "organizations"],
            "Analytics": ["athena", "glue", "kinesis", "emr", "quicksight"],
            "AI/ML": ["sagemaker", "comprehend", "rekognition", "translate", "polly"]
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in service_name_lower:
                    return category
        
        return "Other"
    
    def _save_unified_csv(self, data: List[Dict], output_path: Path):
        """통합 데이터를 CSV로 저장"""
        if not data:
            return
        
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"   �� CSV 파일 저장: {output_path}")
    
    def _save_unified_json(self, data: List[Dict], output_path: Path):
        """통합 데이터를 JSON으로 저장"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"   💾 JSON 파일 저장: {output_path}")
    
    def _save_unification_stats(self, icon_count: int, service_count: int, 
                               product_count: int, taxonomy_count: int, 
                               unified_count: int, output_path: Path):
        """통합 통계 저장"""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "input_data": {
                "icons": icon_count,
                "services": service_count,
                "products": product_count,
                "taxonomy": taxonomy_count
            },
            "output_data": {
                "unified_entries": unified_count
            },
            "processing": {
                "total_input": icon_count + service_count + product_count + taxonomy_count,
                "deduplication_rate": (icon_count + service_count + product_count + taxonomy_count - unified_count) / max(icon_count + service_count + product_count + taxonomy_count, 1)
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"   💾 통계 파일 저장: {output_path}")


def generate_unified_taxonomy(data_dir: str = "out") -> bool:
    """통합 택소노미 생성 함수"""
    generator = UnifiedTaxonomyGenerator(data_dir)
    return generator.generate_unified_taxonomy()


if __name__ == "__main__":
    generate_unified_taxonomy()
