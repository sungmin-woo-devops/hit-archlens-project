"""
AWS 제품 정보 수집기
AWS 공식 API에서 제품 정보를 수집합니다.
"""

import csv
import json
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ProductInfo:
    """제품 정보 데이터 클래스"""
    group: str
    service: str
    service_url: str
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    description: Optional[str] = None

class AWSProductCollector:
    """
    AWS 제품 정보 수집기
    
    AWS 공식 API에서 제품 정보를 수집하여 구조화된 데이터를 생성합니다.
    
    사용 예시:
    ```python
    collector = AWSProductCollector()
    products = collector.collect_products()
    collector.save_products(products, "output.csv", "output.json")
    ```
    """
    
    def __init__(self, api_url: Optional[str] = None):
        """
        초기화
        
        Args:
            api_url: AWS 제품 API URL (기본값 사용 시 None)
        """
        self.api_url = api_url or (
            "https://aws.amazon.com/api/dirs/items/search?"
            "item.directoryId=aws-products&"
            "sort_by=item.additionalFields.productNameLowercase&size=1000&"
            "language=en&item.locale=en_US"
        )
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def collect_products(self, timeout: int = 30) -> List[ProductInfo]:
        """
        AWS 제품 정보 수집
        
        Args:
            timeout: API 요청 타임아웃 (초)
            
        Returns:
            List[ProductInfo]: 제품 정보 리스트
            
        Raises:
            requests.RequestException: API 요청 실패 시
        """
        print(f"🔍 AWS 제품 정보 수집 중... (API: {self.api_url})")
        
        try:
            response = self.session.get(self.api_url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"❌ API 요청 실패: {e}")
            raise
        
        products = []
        items = data.get("items", [])
        
        print(f"📊 발견된 제품: {len(items)}개")
        
        for item in items:
            try:
                product_info = self._parse_product_item(item)
                if product_info:
                    products.append(product_info)
            except Exception as e:
                print(f"⚠️ 제품 파싱 실패: {e}")
                continue
        
        print(f"✅ 성공적으로 파싱된 제품: {len(products)}개")
        return products
    
    def _parse_product_item(self, item: Dict) -> Optional[ProductInfo]:
        """
        제품 아이템 파싱
        
        Args:
            item: API 응답의 제품 아이템
            
        Returns:
            Optional[ProductInfo]: 파싱된 제품 정보
        """
        try:
            item_data = item.get("item", {})
            additional_fields = item_data.get("additionalFields", {})
            
            # 필수 필드 추출
            product_name = additional_fields.get("productName", "")
            product_category = additional_fields.get("productCategory", "")
            product_url = additional_fields.get("productUrl", "")
            
            # URL에서 서비스명 추출
            service_name = self._extract_service_from_url(product_url)
            
            # 그룹명 정규화
            group = self._normalize_group(product_category)
            
            # 설명 추출
            description = additional_fields.get("productDescription", "")
            
            if not product_name or not service_name:
                return None
            
            return ProductInfo(
                group=group,
                service=service_name,
                service_url=product_url,
                product_name=product_name,
                product_category=product_category,
                description=description
            )
            
        except Exception as e:
            print(f"⚠️ 제품 아이템 파싱 실패: {e}")
            return None
    
    def _extract_service_from_url(self, url: str) -> str:
        """
        URL에서 서비스명 추출
        
        Args:
            url: 제품 URL
            
        Returns:
            str: 추출된 서비스명
        """
        if not url:
            return ""
        
        # URL에서 서비스명 추출
        # 예: https://aws.amazon.com/ec2/ -> EC2
        # 예: https://aws.amazon.com/s3/ -> S3
        
        # 마지막 경로에서 서비스명 추출
        path = url.rstrip('/').split('/')[-1]
        
        # 일반적인 서비스명 매핑
        service_mapping = {
            'ec2': 'Amazon EC2',
            's3': 'Amazon S3',
            'rds': 'Amazon RDS',
            'lambda': 'AWS Lambda',
            'dynamodb': 'Amazon DynamoDB',
            'cloudfront': 'Amazon CloudFront',
            'vpc': 'Amazon VPC',
            'iam': 'AWS IAM',
            'sns': 'Amazon SNS',
            'sqs': 'Amazon SQS',
            'cloudwatch': 'Amazon CloudWatch',
            'ecs': 'Amazon ECS',
            'eks': 'Amazon EKS',
            'elb': 'Elastic Load Balancing',
            'autoscaling': 'Auto Scaling',
            'route53': 'Amazon Route 53',
            'cloudformation': 'AWS CloudFormation',
            'codecommit': 'AWS CodeCommit',
            'codebuild': 'AWS CodeBuild',
            'codedeploy': 'AWS CodeDeploy',
            'codepipeline': 'AWS CodePipeline',
            'elasticache': 'Amazon ElastiCache',
            'redshift': 'Amazon Redshift',
            'emr': 'Amazon EMR',
            'glue': 'AWS Glue',
            'athena': 'Amazon Athena',
            'quicksight': 'Amazon QuickSight',
            'sagemaker': 'Amazon SageMaker',
            'rekognition': 'Amazon Rekognition',
            'comprehend': 'Amazon Comprehend',
            'translate': 'Amazon Translate',
            'polly': 'Amazon Polly',
            'lex': 'Amazon Lex',
            'connect': 'Amazon Connect',
            'chime': 'Amazon Chime',
            'workspaces': 'Amazon WorkSpaces',
            'appstream': 'Amazon AppStream',
            'lightsail': 'Amazon Lightsail',
            'elasticbeanstalk': 'AWS Elastic Beanstalk',
            'opsworks': 'AWS OpsWorks',
            'config': 'AWS Config',
            'cloudtrail': 'AWS CloudTrail',
            'guardduty': 'Amazon GuardDuty',
            'macie': 'Amazon Macie',
            'shield': 'AWS Shield',
            'waf': 'AWS WAF',
            'kms': 'AWS Key Management Service',
            'secretsmanager': 'AWS Secrets Manager',
            'certificatemanager': 'AWS Certificate Manager',
            'directoryservice': 'AWS Directory Service',
            'cognito': 'Amazon Cognito',
            'organizations': 'AWS Organizations',
            'budgets': 'AWS Budgets',
            'costexplorer': 'AWS Cost Explorer',
            'billing': 'AWS Billing',
            'support': 'AWS Support',
            'marketplace': 'AWS Marketplace',
            'ram': 'AWS Resource Access Manager',
            'servicecatalog': 'AWS Service Catalog',
            'systemsmanager': 'AWS Systems Manager',
            'cloud9': 'AWS Cloud9',
            'xray': 'AWS X-Ray',
            'stepfunctions': 'AWS Step Functions',
            'apigateway': 'Amazon API Gateway',
            'appsync': 'AWS AppSync',
            'eventbridge': 'Amazon EventBridge',
            'mq': 'Amazon MQ',
            'kinesis': 'Amazon Kinesis',
            'msk': 'Amazon MSK',
            'elasticsearch': 'Amazon Elasticsearch Service',
            'opensearch': 'Amazon OpenSearch Service',
            'neptune': 'Amazon Neptune',
            'documentdb': 'Amazon DocumentDB',
            'timestream': 'Amazon Timestream',
            'keyspaces': 'Amazon Keyspaces',
            'qldb': 'Amazon QLDB',
            'managedblockchain': 'Amazon Managed Blockchain',
            'iot': 'AWS IoT',
            'greengrass': 'AWS IoT Greengrass',
            'iotanalytics': 'AWS IoT Analytics',
            'iotsitewise': 'AWS IoT SiteWise',
            'iotthingsgraph': 'AWS IoT Things Graph',
            'freertos': 'Amazon FreeRTOS',
            'robomaker': 'AWS RoboMaker',
            'groundstation': 'AWS Ground Station',
            'batch': 'AWS Batch',
            'parallelcluster': 'AWS ParallelCluster',
            'thinkbox': 'AWS Thinkbox',
            'nimblestudio': 'Amazon Nimble Studio',
            'elemental': 'AWS Elemental',
            'ivs': 'Amazon Interactive Video Service',
            'medialive': 'AWS MediaLive',
            'mediapackage': 'AWS MediaPackage',
            'mediastore': 'AWS MediaStore',
            'mediaconvert': 'AWS MediaConvert',
            'elementalmediaconnect': 'AWS Elemental MediaConnect',
            'elementalmedialive': 'AWS Elemental MediaLive',
            'elementalmediapackage': 'AWS Elemental MediaPackage',
            'elementalmediastore': 'AWS Elemental MediaStore',
            'elementalmediaconvert': 'AWS Elemental MediaConvert',
            'elementalmediatailor': 'AWS Elemental MediaTailor',
            'elementalmediaconnect': 'AWS Elemental MediaConnect',
            'elementalmedialive': 'AWS Elemental MediaLive',
            'elementalmediapackage': 'AWS Elemental MediaPackage',
            'elementalmediastore': 'AWS Elemental MediaStore',
            'elementalmediaconvert': 'AWS Elemental MediaConvert',
            'elementalmediatailor': 'AWS Elemental MediaTailor',
        }
        
        # 매핑에서 찾기
        if path.lower() in service_mapping:
            return service_mapping[path.lower()]
        
        # 매핑에 없으면 URL에서 추출
        if path:
            # 첫 글자 대문자로 변환
            return path.upper()
        
        return ""
    
    def _normalize_group(self, category: str) -> str:
        """
        카테고리를 그룹명으로 정규화
        
        Args:
            category: 원본 카테고리명
            
        Returns:
            str: 정규화된 그룹명
        """
        if not category:
            return "Other"
        
        # 카테고리 매핑
        category_mapping = {
            "Compute": "Compute",
            "Storage": "Storage",
            "Database": "Database",
            "Networking & Content Delivery": "Networking & Content Delivery",
            "Security, Identity, & Compliance": "Security, Identity, & Compliance",
            "Management & Governance": "Management & Governance",
            "Application Integration": "Application Integration",
            "Analytics": "Analytics",
            "Artificial Intelligence": "Artificial Intelligence",
            "Machine Learning": "Machine Learning",
            "Media Services": "Media Services",
            "Developer Tools": "Developer Tools",
            "Front-End Web & Mobile": "Front-End Web & Mobile",
            "End User Computing": "End User Computing",
            "Internet of Things": "Internet of Things",
            "Migration & Modernization": "Migration & Modernization",
            "Quantum Technologies": "Quantum Technologies",
            "Robotics": "Robotics",
            "Satellite": "Satellite",
            "Blockchain": "Blockchain",
            "Business Applications": "Business Applications",
            "Cloud Financial Management": "Cloud Financial Management",
            "Customer Enablement": "Customer Enablement",
            "Games": "Games",
            "General": "General",
        }
        
        return category_mapping.get(category, category)
    
    def save_products(self, products: List[ProductInfo], 
                     csv_path: str, json_path: str) -> None:
        """
        제품 정보를 CSV와 JSON 파일로 저장
        
        Args:
            products: 제품 정보 리스트
            csv_path: CSV 출력 파일 경로
            json_path: JSON 출력 파일 경로
        """
        # 출력 디렉터리 생성
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        
        # CSV 저장
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["group", "service", "service_url", "product_name", "product_category", "description"])
            for product in products:
                w.writerow([
                    product.group,
                    product.service,
                    product.service_url,
                    product.product_name,
                    product.product_category,
                    product.description
                ])
        
        # JSON 저장
        json_data = []
        for product in products:
            json_data.append({
                "group": product.group,
                "service": product.service,
                "service_url": product.service_url,
                "product_name": product.product_name,
                "product_category": product.product_category,
                "description": product.description
            })
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ CSV: {csv_path}  rows={len(products)}")
        print(f"✅ JSON: {json_path}  rows={len(products)}")
    
    def get_statistics(self, products: List[ProductInfo]) -> Dict:
        """제품 정보 통계"""
        stats = {
            "total_products": len(products),
            "groups": {},
            "services": {}
        }
        
        for product in products:
            # 그룹별 통계
            stats["groups"][product.group] = stats["groups"].get(product.group, 0) + 1
            
            # 서비스별 통계
            stats["services"][product.service] = stats["services"].get(product.service, 0) + 1
        
        return stats
