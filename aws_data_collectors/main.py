"""
AWS 데이터 수집기 메인 모듈
세 가지 수집기를 통합하여 AWS 관련 데이터를 수집합니다.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional
import yaml

from collectors.icon_collector import AWSIconCollector
from collectors.product_collector import AWSProductCollector
from collectors.service_collector import AWSServiceCollector

class AWSDataCollector:
    """
    AWS 데이터 수집기 메인 클래스
    
    세 가지 수집기를 통합하여 AWS 관련 데이터를 수집합니다:
    - 아이콘 수집기: AWS 공식 아이콘 ZIP 파일 파싱
    - 제품 수집기: AWS 공식 API에서 제품 정보 수집
    - 서비스 수집기: boto3를 통한 서비스 메타데이터 수집
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        초기화
        
        Args:
            config_path: 설정 파일 경로 (기본값: config.yaml)
        """
        self.config = self._load_config(config_path)
        self.icon_collector = AWSIconCollector()
        self.product_collector = AWSProductCollector()
        self.service_collector = AWSServiceCollector()
        
        # 출력 디렉터리 생성
        self._create_output_dirs()
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """설정 파일 로드"""
        if config_path is None:
            config_path = "config.yaml"
        
        if not os.path.exists(config_path):
            print(f"⚠️ 설정 파일이 없습니다: {config_path}")
            return self._get_default_config()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print(f"✅ 설정 파일 로드: {config_path}")
            return config
        except Exception as e:
            print(f"❌ 설정 파일 로드 실패: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """기본 설정"""
        return {
            "collectors": {
                "icons": {
                    "zip_path": "Asset-Package.zip",
                    "output_dir": "data/icons"
                },
                "products": {
                    "api_url": "https://aws.amazon.com/api/dirs/items/search?item.directoryId=aws-products&sort_by=item.additionalFields.productNameLowercase&size=1000&language=en&item.locale=en_US",
                    "output_dir": "data/products"
                },
                "services": {
                    "output_dir": "data/services"
                }
            },
            "exporters": {
                "formats": ["csv", "json"],
                "unified_output": "data/unified"
            }
        }
    
    def _create_output_dirs(self):
        """출력 디렉터리 생성"""
        dirs = [
            self.config["collectors"]["icons"]["output_dir"],
            self.config["collectors"]["products"]["output_dir"],
            self.config["collectors"]["services"]["output_dir"],
            self.config["exporters"]["unified_output"]
        ]
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"📁 디렉터리 생성: {dir_path}")
    
    def collect_icons(self) -> bool:
        """
        AWS 아이콘 수집
        
        Returns:
            bool: 성공 여부
        """
        try:
            print("\n🎨 AWS 아이콘 수집 시작...")
            
            zip_path = self.config["collectors"]["icons"]["zip_path"]
            output_dir = self.config["collectors"]["icons"]["output_dir"]
            
            if not os.path.exists(zip_path):
                print(f"❌ 아이콘 ZIP 파일이 없습니다: {zip_path}")
                return False
            
            # 아이콘 수집
            mappings = self.icon_collector.collect_icons(zip_path)
            
            if not mappings:
                print("❌ 수집된 아이콘이 없습니다.")
                return False
            
            # 파일 저장
            csv_path = os.path.join(output_dir, "aws_icons_mapping.csv")
            json_path = os.path.join(output_dir, "aws_icons_mapping.json")
            
            self.icon_collector.save_mappings(mappings, csv_path, json_path)
            
            # 통계 출력
            stats = self.icon_collector.get_statistics(mappings)
            print(f"📊 아이콘 통계:")
            print(f"   - 총 아이콘: {stats['total_icons']}개")
            print(f"   - 그룹 수: {len(stats['groups'])}개")
            print(f"   - 서비스 수: {len(stats['services'])}개")
            
            return True
            
        except Exception as e:
            print(f"❌ 아이콘 수집 실패: {e}")
            return False
    
    def collect_products(self) -> bool:
        """
        AWS 제품 정보 수집
        
        Returns:
            bool: 성공 여부
        """
        try:
            print("\n🛍️ AWS 제품 정보 수집 시작...")
            
            output_dir = self.config["collectors"]["products"]["output_dir"]
            
            # 제품 정보 수집
            products = self.product_collector.collect_products()
            
            if not products:
                print("❌ 수집된 제품 정보가 없습니다.")
                return False
            
            # 파일 저장
            csv_path = os.path.join(output_dir, "aws_products.csv")
            json_path = os.path.join(output_dir, "aws_products.json")
            
            self.product_collector.save_products(products, csv_path, json_path)
            
            # 통계 출력
            stats = self.product_collector.get_statistics(products)
            print(f"📊 제품 통계:")
            print(f"   - 총 제품: {stats['total_products']}개")
            print(f"   - 그룹 수: {len(stats['groups'])}개")
            print(f"   - 서비스 수: {len(stats['services'])}개")
            
            return True
            
        except Exception as e:
            print(f"❌ 제품 정보 수집 실패: {e}")
            return False
    
    def collect_services(self) -> bool:
        """
        AWS 서비스 정보 수집
        
        Returns:
            bool: 성공 여부
        """
        try:
            print("\n🔧 AWS 서비스 정보 수집 시작...")
            
            output_dir = self.config["collectors"]["services"]["output_dir"]
            
            # 서비스 정보 수집
            services = self.service_collector.collect_services()
            resources = self.service_collector.infer_resources()
            
            if not services:
                print("❌ 수집된 서비스 정보가 없습니다.")
                return False
            
            # 파일 저장
            services_csv = os.path.join(output_dir, "aws_services.csv")
            services_json = os.path.join(output_dir, "aws_services.json")
            resources_csv = os.path.join(output_dir, "aws_resources.csv")
            resources_json = os.path.join(output_dir, "aws_resources.json")
            
            self.service_collector.save_services(services, services_csv, services_json)
            self.service_collector.save_resources(resources, resources_csv, resources_json)
            
            # 통계 출력
            stats = self.service_collector.get_statistics(services, resources)
            print(f"📊 서비스 통계:")
            print(f"   - 총 서비스: {stats['total_services']}개")
            print(f"   - 리소스 추론: {stats['total_resources']}개")
            print(f"   - 글로벌 서비스: {stats['global_services']}개")
            print(f"   - 리소스 인터페이스: {stats['resource_services']}개")
            print(f"   - 평균 리전 수: {stats['avg_regions']:.1f}")
            
            return True
            
        except Exception as e:
            print(f"❌ 서비스 정보 수집 실패: {e}")
            return False
    
    def collect_all(self) -> bool:
        """
        모든 데이터 수집
        
        Returns:
            bool: 성공 여부
        """
        print("🚀 AWS 데이터 수집 시작...")
        
        success_count = 0
        total_count = 3
        
        # 아이콘 수집
        if self.collect_icons():
            success_count += 1
        
        # 제품 정보 수집
        if self.collect_products():
            success_count += 1
        
        # 서비스 정보 수집
        if self.collect_services():
            success_count += 1
        
        print(f"\n🎉 수집 완료: {success_count}/{total_count} 성공")
        
        if success_count == total_count:
            print("✅ 모든 데이터 수집이 성공적으로 완료되었습니다!")
            return True
        else:
            print("⚠️ 일부 데이터 수집에 실패했습니다.")
            return False
    
    def get_collection_status(self) -> Dict:
        """수집 상태 확인"""
        status = {
            "icons": {
                "csv": os.path.exists(os.path.join(self.config["collectors"]["icons"]["output_dir"], "aws_icons_mapping.csv")),
                "json": os.path.exists(os.path.join(self.config["collectors"]["icons"]["output_dir"], "aws_icons_mapping.json"))
            },
            "products": {
                "csv": os.path.exists(os.path.join(self.config["collectors"]["products"]["output_dir"], "aws_products.csv")),
                "json": os.path.exists(os.path.join(self.config["collectors"]["products"]["output_dir"], "aws_products.json"))
            },
            "services": {
                "csv": os.path.exists(os.path.join(self.config["collectors"]["services"]["output_dir"], "aws_services.csv")),
                "json": os.path.exists(os.path.join(self.config["collectors"]["services"]["output_dir"], "aws_services.json")),
                "resources_csv": os.path.exists(os.path.join(self.config["collectors"]["services"]["output_dir"], "aws_resources.csv")),
                "resources_json": os.path.exists(os.path.join(self.config["collectors"]["services"]["output_dir"], "aws_resources.json"))
            }
        }
        return status


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AWS 데이터 수집기")
    parser.add_argument("--config", "-c", help="설정 파일 경로")
    parser.add_argument("--icons-only", action="store_true", help="아이콘만 수집")
    parser.add_argument("--products-only", action="store_true", help="제품 정보만 수집")
    parser.add_argument("--services-only", action="store_true", help="서비스 정보만 수집")
    parser.add_argument("--status", action="store_true", help="수집 상태 확인")
    
    args = parser.parse_args()
    
    # 수집기 초기화
    collector = AWSDataCollector(args.config)
    
    if args.status:
        # 상태 확인
        status = collector.get_collection_status()
        print("📊 수집 상태:")
        for category, files in status.items():
            print(f"  {category}:")
            for file_type, exists in files.items():
                print(f"    {file_type}: {'✅' if exists else '❌'}")
        return
    
    # 수집 실행
    if args.icons_only:
        collector.collect_icons()
    elif args.products_only:
        collector.collect_products()
    elif args.services_only:
        collector.collect_services()
    else:
        collector.collect_all()


if __name__ == "__main__":
    main()
