"""
AWS Data Collector Implementation

AWS 데이터 수집을 위한 구체적인 구현체
"""

import time
import json
import csv
import zipfile
import boto3
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import threading
from datetime import datetime

from .base_collector import BaseDataCollector, CollectionResult, CollectionStatistics
from ..models import AWSServiceInfo, AWSServiceIcon


class AWSDataCollector(BaseDataCollector):
    """
    AWS 데이터 수집기
    
    AWS 아이콘, 서비스 정보, 제품 정보를 수집하는 구현체
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        AWS 데이터 수집기 초기화
        
        Args:
            config: AWS 전용 설정
        """
        super().__init__("aws", config)
        
        # AWS 특화 설정
        self.region = config.get("region", "us-east-1")
        self.collectors_config = config.get("collectors", {})
        
        # 출력 디렉터리 설정
        self.icons_output_dir = self.output_dir / "aws" / "icons"
        self.services_output_dir = self.output_dir / "aws" / "services"
        self.products_output_dir = self.output_dir / "aws" / "products"
        
        # 디렉터리 생성
        for dir_path in [self.icons_output_dir, self.services_output_dir, self.products_output_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 진행 상황 모니터링
        self.progress_lock = threading.Lock()
        self.current_task = ""
        self.progress_percentage = 0
        self.detailed_status = {}
        
        print(f"✅ AWS 데이터 수집기 초기화 완료")
        print(f"   - 리전: {self.region}")
        print(f"   - 출력 디렉터리: {self.output_dir}")
    
    def get_supported_data_types(self) -> List[str]:
        """
        지원하는 데이터 타입 목록 반환
        
        Returns:
            List[str]: 지원하는 데이터 타입 목록
        """
        return ["icons", "services", "products"]
    
    def validate_data(self, data: Any) -> bool:
        """
        수집된 데이터 검증
        
        Args:
            data: 검증할 데이터
            
        Returns:
            bool: 유효성 여부
        """
        if isinstance(data, list):
            return len(data) > 0
        elif isinstance(data, dict):
            return len(data) > 0
        else:
            return data is not None
    
    def _collect_specific_impl(self, data_type: str) -> CollectionResult:
        """
        특정 데이터 타입 수집 구현
        
        Args:
            data_type: 수집할 데이터 타입
            
        Returns:
            CollectionResult: 수집 결과
        """
        if data_type == "icons":
            return self._collect_icons()
        elif data_type == "services":
            return self._collect_services()
        elif data_type == "products":
            return self._collect_products()
        else:
            return CollectionResult(
                success=False,
                data_count=0,
                processing_time=0,
                output_paths=[],
                errors=[f"지원하지 않는 데이터 타입: {data_type}"]
            )
    
    def collect(self) -> CollectionResult:
        """
        AWS 데이터 수집 실행 (기존 메서드 유지)
        
        Returns:
            CollectionResult: 수집 결과
        """
        print("📊 AWS 데이터 수집 시작")
        print("=" * 50)
        
        start_time = time.time()
        all_results = {}
        
        # 수집할 데이터 타입 결정
        data_types = self.config.get("data_types", ["icons", "services", "products"])
        
        for data_type in data_types:
            print(f"\n🔍 {data_type.upper()} 데이터 수집 중...")
            self.current_task = data_type
            
            result = self._collect_specific_impl(data_type)
            all_results[data_type] = result
            
            # 결과 출력
            if result.success:
                print(f"✅ {data_type} 수집 완료: {result.data_count}개 항목 ({result.processing_time:.2f}초)")
            else:
                print(f"❌ {data_type} 수집 실패: {', '.join(result.errors)}")
        
        # 전체 통계 계산
        total_time = time.time() - start_time
        total_count = sum(r.data_count for r in all_results.values() if r.success)
        success_count = sum(1 for r in all_results.values() if r.success)
        
        print("\n" + "=" * 50)
        print(f" 수집 완료 요약")
        print(f"   - 총 처리 시간: {total_time:.2f}초")
        print(f"   - 성공한 수집: {success_count}/{len(data_types)}")
        print(f"   - 총 수집 항목: {total_count}개")
        
        return CollectionResult(
            success=success_count > 0,
            data_count=total_count,
            processing_time=total_time,
            output_paths=[path for r in all_results.values() for path in r.output_paths if r.success],
            errors=[error for r in all_results.values() for error in r.errors if not r.success]
        )
    
    def _collect_icons(self) -> CollectionResult:
        """AWS 아이콘 수집 (개선된 버전)"""
        start_time = time.time()
        
        try:
            icons_config = self.collectors_config.get("icons", {})
            zip_path = icons_config.get("zip_path", "Asset-Package.zip")
            
            if not Path(zip_path).exists():
                return CollectionResult(
                    success=False,
                    data_count=0,
                    processing_time=time.time() - start_time,
                    output_paths=[],
                    errors=[f"아이콘 ZIP 파일을 찾을 수 없습니다: {zip_path}"]
                )
            
            print(f"   📦 ZIP 파일 분석 중: {zip_path}")
            
            # ZIP 파일 정보 분석
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                icon_files = [f for f in zip_file.filelist if f.filename.endswith(('.svg', '.png'))]
                total_files = len(icon_files)
                
                print(f"    총 {total_files:,}개 아이콘 파일 발견")
                
                # 진행 상황 표시
                with tqdm(total=total_files, desc="아이콘 파싱", unit="파일") as pbar:
                    icon_mappings = []
                    
                    for file_info in icon_files:
                        icon_info = self._extract_icon_info(file_info.filename)
                        if icon_info:
                            icon_mappings.append(icon_info)
                        pbar.update(1)
                        
                        # 진행 상황 업데이트
                        with self.progress_lock:
                            self.progress_percentage = (len(icon_mappings) / total_files) * 100
                            self.detailed_status = {
                                "processed": len(icon_mappings),
                                "total": total_files,
                                "current_file": file_info.filename
                            }
            
            # CSV 및 JSON 파일로 저장
            csv_path = self.icons_output_dir / "aws_icons_mapping.csv"
            json_path = self.icons_output_dir / "aws_icons_mapping.json"
            
            print(f"   💾 파일 저장 중...")
            self._save_icon_mappings_csv(icon_mappings, csv_path)
            self._save_icon_mappings_json(icon_mappings, json_path)
            
            processing_time = time.time() - start_time
            
            return CollectionResult(
                success=True,
                data_count=len(icon_mappings),
                processing_time=processing_time,
                output_paths=[str(csv_path), str(json_path)]
            )
            
        except Exception as e:
            return CollectionResult(
                success=False,
                data_count=0,
                processing_time=time.time() - start_time,
                output_paths=[],
                errors=[str(e)]
            )
    
    def _collect_services(self) -> CollectionResult:
        """AWS 서비스 정보 수집 (개선된 버전)"""
        start_time = time.time()
        
        try:
            print(f"   🔧 boto3 세션 생성 중...")
            session = boto3.Session(region_name=self.region)
            available_services = session.get_available_services()
            
            print(f"   📋 {len(available_services)}개 서비스 발견")
            
            # 병렬 처리를 위한 설정
            max_workers = min(10, len(available_services))  # 최대 10개 스레드
            service_infos = []
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 작업 제출
                future_to_service = {
                    executor.submit(self._collect_single_service, session, service_name): service_name
                    for service_name in available_services
                }
                
                # 진행 상황 표시
                with tqdm(total=len(available_services), desc="서비스 정보 수집", unit="서비스") as pbar:
                    for future in as_completed(future_to_service):
                        service_name = future_to_service[future]
                        try:
                            service_info = future.result()
                            if service_info:
                                service_infos.append(service_info)
                        except Exception as e:
                            print(f"   ⚠️ {service_name} 처리 실패: {e}")
                        
                        pbar.update(1)
                        
                        # 진행 상황 업데이트
                        with self.progress_lock:
                            self.progress_percentage = (len(service_infos) / len(available_services)) * 100
                            self.detailed_status = {
                                "processed": len(service_infos),
                                "total": len(available_services),
                                "current_service": service_name
                            }
            
            # CSV 및 JSON 파일로 저장
            csv_path = self.services_output_dir / "aws_services.csv"
            json_path = self.services_output_dir / "aws_services.json"
            
            print(f"   💾 파일 저장 중...")
            self._save_service_infos_csv(service_infos, csv_path)
            self._save_service_infos_json(service_infos, json_path)
            
            processing_time = time.time() - start_time
            
            return CollectionResult(
                success=True,
                data_count=len(service_infos),
                processing_time=processing_time,
                output_paths=[str(csv_path), str(json_path)]
            )
            
        except Exception as e:
            return CollectionResult(
                success=False,
                data_count=0,
                processing_time=time.time() - start_time,
                output_paths=[],
                errors=[str(e)]
            )
    
    def _collect_single_service(self, session: boto3.Session, service_name: str) -> Optional[AWSServiceInfo]:
        """단일 서비스 정보 수집"""
        try:
            client = session.client(service_name)
            
            service_info = AWSServiceInfo(
                service_code=service_name,
                service_name=self._get_service_full_name(service_name),
                regions=client.meta.region_name,
                main_resource_example=self._infer_main_resource(service_name)
            )
            
            return service_info
            
        except Exception:
            return None
    
    def _collect_products(self) -> CollectionResult:
        """AWS 제품 정보 수집"""
        start_time = time.time()
        
        try:
            products_config = self.collectors_config.get("products", {})
            api_url = products_config.get("api_url")
            
            if not api_url:
                return CollectionResult(
                    success=False,
                    data_count=0,
                    processing_time=time.time() - start_time,
                    output_paths=[],
                    errors=["제품 API URL이 설정되지 않았습니다"]
                )
            
            # API를 통한 제품 정보 수집
            product_infos = self._collect_product_info(api_url)
            
            # CSV 및 JSON 파일로 저장
            csv_path = self.products_output_dir / "aws_products.csv"
            json_path = self.products_output_dir / "aws_products.json"
            
            self._save_product_infos_csv(product_infos, csv_path)
            self._save_product_infos_json(product_infos, json_path)
            
            processing_time = time.time() - start_time
            
            return CollectionResult(
                success=True,
                data_count=len(product_infos),
                processing_time=processing_time,
                output_paths=[str(csv_path), str(json_path)]
            )
            
        except Exception as e:
            return CollectionResult(
                success=False,
                data_count=0,
                processing_time=time.time() - start_time,
                output_paths=[],
                errors=[str(e)]
            )
    
    def _parse_icon_zip(self, zip_path: str) -> List[AWSServiceIcon]:
        """아이콘 ZIP 파일 파싱"""
        icon_mappings = []
        
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            for file_info in zip_file.filelist:
                if file_info.filename.endswith(('.svg', '.png')):
                    # 파일 경로에서 정보 추출
                    icon_info = self._extract_icon_info(file_info.filename)
                    if icon_info:
                        icon_mappings.append(icon_info)
        
        return icon_mappings
    
    def _extract_icon_info(self, file_path: str) -> Optional[AWSServiceIcon]:
        """파일 경로에서 아이콘 정보 추출"""
        try:
            # 경로 파싱
            parts = Path(file_path).parts
            
            # Resource-Icons_ 날짜 형식 찾기
            resource_root = None
            for part in parts:
                if part.startswith("Resource-Icons_"):
                    resource_root = part
                    break
            
            if not resource_root:
                return None
            
            # 그룹과 서비스 추출
            group = None
            service = None
            
            for i, part in enumerate(parts):
                if part.startswith("Res_") and i < len(parts) - 1:
                    group = part[4:].replace("-", " ")  # Res_ 제거
                    service = parts[i + 1][4:].replace("-", " ")  # Res_ 제거
                    break
            
            if not group or not service:
                return None
            
            return AWSServiceIcon(
                group=group,
                service=service,
                zip_path=file_path,
                file_path=file_path
            )
            
        except Exception:
            return None
    
    def _collect_service_metadata(self) -> List[AWSServiceInfo]:
        """boto3를 통한 서비스 메타데이터 수집"""
        service_infos = []
        
        # boto3 세션 생성
        session = boto3.Session(region_name=self.region)
        
        # 사용 가능한 서비스 목록
        available_services = session.get_available_services()
        
        for service_name in available_services:
            try:
                # 서비스 클라이언트 생성
                client = session.client(service_name)
                
                # 서비스 정보 추출
                service_info = AWSServiceInfo(
                    service_code=service_name,
                    service_name=self._get_service_full_name(service_name),
                    regions=client.meta.region_name,
                    main_resource_example=self._infer_main_resource(service_name)
                )
                
                service_infos.append(service_info)
                
            except Exception as e:
                print(f"⚠️ {service_name} 서비스 정보 수집 실패: {e}")
                continue
        
        return service_infos
    
    def _get_service_full_name(self, service_code: str) -> str:
        """서비스 코드를 전체 이름으로 변환"""
        # AWS 서비스 코드 매핑
        service_names = {
            "ec2": "Amazon Elastic Compute Cloud",
            "s3": "Amazon Simple Storage Service",
            "lambda": "AWS Lambda",
            "rds": "Amazon Relational Database Service",
            "dynamodb": "Amazon DynamoDB",
            "cloudfront": "Amazon CloudFront",
            "apigateway": "Amazon API Gateway",
            "sns": "Amazon Simple Notification Service",
            "sqs": "Amazon Simple Queue Service",
            "cloudwatch": "Amazon CloudWatch",
            "iam": "AWS Identity and Access Management",
            "vpc": "Amazon Virtual Private Cloud",
            "elb": "Elastic Load Balancing",
            "autoscaling": "Auto Scaling",
            "ecs": "Amazon Elastic Container Service",
            "eks": "Amazon Elastic Kubernetes Service",
            "codebuild": "AWS CodeBuild",
            "codepipeline": "AWS CodePipeline",
            "cloudformation": "AWS CloudFormation",
            "route53": "Amazon Route 53"
        }
        
        return service_names.get(service_code, f"AWS {service_code.upper()}")
    
    def _infer_main_resource(self, service_code: str) -> str:
        """서비스 코드에서 대표 리소스 추론"""
        resource_mapping = {
            "ec2": "Instance",
            "s3": "Bucket",
            "lambda": "Function",
            "rds": "DBInstance",
            "dynamodb": "Table",
            "cloudfront": "Distribution",
            "apigateway": "RestApi",
            "sns": "Topic",
            "sqs": "Queue",
            "cloudwatch": "Alarm",
            "iam": "Role",
            "vpc": "Vpc",
            "elb": "LoadBalancer",
            "autoscaling": "AutoScalingGroup",
            "ecs": "Cluster",
            "eks": "Cluster",
            "codebuild": "Project",
            "codepipeline": "Pipeline",
            "cloudformation": "Stack",
            "route53": "HostedZone"
        }
        
        return resource_mapping.get(service_code, "Resource")
    
    def _collect_product_info(self, api_url: str) -> List[Dict[str, Any]]:
        """AWS 제품 API에서 정보 수집"""
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            products = data.get("items", [])
            
            return products
            
        except Exception as e:
            print(f"❌ 제품 정보 수집 실패: {e}")
            return []
    
    def _save_icon_mappings_csv(self, icon_mappings: List[AWSServiceIcon], output_path: Path) -> None:
        """아이콘 매핑을 CSV로 저장"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['group', 'service', 'zip_path', 'category', 'file_path'])
            
            for icon in icon_mappings:
                writer.writerow([
                    icon.group,
                    icon.service,
                    icon.zip_path,
                    icon.category or '',
                    icon.file_path or ''
                ])
    
    def _save_icon_mappings_json(self, icon_mappings: List[AWSServiceIcon], output_path: Path) -> None:
        """아이콘 매핑을 JSON으로 저장"""
        data = [icon.to_dict() for icon in icon_mappings]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _save_service_infos_csv(self, service_infos: List[AWSServiceInfo], output_path: Path) -> None:
        """서비스 정보를 CSV로 저장"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['service_code', 'service_name', 'regions', 'main_resource_example'])
            for service in service_infos:
                writer.writerow([
                    service.service_code,
                    service.service_name,
                    service.regions,
                    service.main_resource_example or ''
                ])
    
    def _save_service_infos_json(self, service_infos: List[AWSServiceInfo], output_path: Path) -> None:
        """서비스 정보를 JSON으로 저장"""
        data = [service.to_dict() for service in service_infos]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _save_product_infos_csv(self, product_infos: List[Dict[str, Any]], output_path: Path) -> None:
        """제품 정보를 CSV로 저장"""
        if not product_infos:
            return
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # 첫 번째 제품의 키를 헤더로 사용
            headers = list(product_infos[0].keys())
            writer.writerow(headers)
            for product in product_infos:
                writer.writerow([product.get(header, '') for header in headers])
    
    def _save_product_infos_json(self, product_infos: List[Dict[str, Any]], output_path: Path) -> None:
        """제품 정보를 JSON으로 저장"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(product_infos, f, indent=2, ensure_ascii=False)
    
    def get_progress(self) -> Dict[str, Any]:
        """현재 진행 상황 반환"""
        with self.progress_lock:
            return {
                "current_task": self.current_task,
                "progress_percentage": self.progress_percentage,
                "detailed_status": self.detailed_status,
                "timestamp": datetime.now().isoformat()
            }
