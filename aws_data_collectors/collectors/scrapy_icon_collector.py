"""
Scrapy를 사용한 AWS 아이콘 웹 수집기
웹에서 AWS 아이콘 이미지를 검색하고 다운로드하여 훈련 데이터셋을 보강합니다.
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
import requests
from PIL import Image
import io

@dataclass
class WebIconData:
    """웹에서 수집된 아이콘 데이터"""
    service_name: str
    source_url: str
    image_url: str
    file_path: str
    file_size: int
    image_width: int
    image_height: int
    confidence_score: float
    search_query: str
    timestamp: str

class ScrapyIconCollector:
    """
    Scrapy를 사용한 AWS 아이콘 웹 수집기
    
    다양한 소스에서 AWS 아이콘을 검색하고 다운로드하여 훈련 데이터셋을 보강합니다.
    
    사용 예시:
    ```python
    collector = ScrapyIconCollector()
    icons = collector.collect_from_google_images("AWS EC2 icon")
    collector.save_collection(icons, "web_icons.json")
    ```
    """
    
    def __init__(self, output_dir: str = "collected_icons"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # AWS 서비스 목록 (기본)
        self.aws_services = [
            "EC2", "S3", "Lambda", "RDS", "DynamoDB", "CloudFront", "VPC",
            "IAM", "CloudWatch", "SQS", "SNS", "API Gateway", "Elastic Beanstalk",
            "ECS", "EKS", "Fargate", "CodeBuild", "CodeDeploy", "CodePipeline",
            "CloudFormation", "Route 53", "ElastiCache", "Redshift", "EMR",
            "Glue", "Athena", "QuickSight", "SageMaker", "Comprehend", "Rekognition",
            "Transcribe", "Translate", "Polly", "Lex", "Connect", "Chime",
            "WorkSpaces", "AppStream", "GameLift", "MediaLive", "MediaConvert",
            "Kinesis", "MSK", "MQ", "Step Functions", "EventBridge", "Config",
            "GuardDuty", "Macie", "Secrets Manager", "KMS", "Cognito", "WAF",
            "Shield", "Certificate Manager", "CloudTrail", "Organizations"
        ]
        
        # 검색 엔진 설정
        self.search_engines = {
            "google": "https://www.google.com/search",
            "bing": "https://www.bing.com/images/search",
            "duckduckgo": "https://duckduckgo.com/"
        }
        
        # User-Agent 설정
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def generate_search_queries(self, service_name: str) -> List[str]:
        """서비스명으로부터 검색 쿼리 생성"""
        queries = [
            f"AWS {service_name} icon",
            f"Amazon {service_name} icon",
            f"{service_name} AWS service icon",
            f"AWS {service_name} logo",
            f"Amazon {service_name} logo",
            f"{service_name} cloud icon",
            f"AWS {service_name} PNG",
            f"AWS {service_name} SVG"
        ]
        return queries
    
    def download_image(self, url: str, filename: str) -> Optional[Dict]:
        """이미지 다운로드 및 메타데이터 추출"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # 이미지 검증
            try:
                img = Image.open(io.BytesIO(response.content))
                img.verify()
            except Exception:
                return None  # 유효하지 않은 이미지
            
            # 다시 열어서 메타데이터 추출
            img = Image.open(io.BytesIO(response.content))
            
            # 파일 저장
            file_path = self.output_dir / filename
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return {
                "file_size": len(response.content),
                "image_width": img.width,
                "image_height": img.height,
                "file_path": str(file_path)
            }
            
        except Exception as e:
            print(f"다운로드 실패: {url} - {e}")
            return None
    
    def collect_from_google_images(self, query: str, max_results: int = 10) -> List[WebIconData]:
        """Google Images에서 아이콘 수집 (시뮬레이션)"""
        # 실제 구현에서는 Google Custom Search API나 Selenium을 사용
        # 여기서는 시뮬레이션으로 구현
        print(f"Google Images에서 '{query}' 검색 중...")
        
        # 실제로는 여기서 웹 스크래핑 로직이 들어감
        # 현재는 더미 데이터로 시뮬레이션
        collected_icons = []
        
        # 더미 이미지 URL들 (실제로는 스크래핑 결과)
        dummy_urls = [
            f"https://example.com/aws_{query.lower().replace(' ', '_')}_1.png",
            f"https://example.com/aws_{query.lower().replace(' ', '_')}_2.png",
            f"https://example.com/aws_{query.lower().replace(' ', '_')}_3.png"
        ]
        
        for i, url in enumerate(dummy_urls[:max_results]):
            service_name = query.replace("AWS ", "").replace(" icon", "").replace(" logo", "")
            filename = f"{service_name.lower()}_{i+1}_{int(time.time())}.png"
            
            # 실제 다운로드 시뮬레이션
            metadata = self.download_image(url, filename)
            if metadata:
                icon_data = WebIconData(
                    service_name=service_name,
                    source_url="Google Images",
                    image_url=url,
                    file_path=metadata["file_path"],
                    file_size=metadata["file_size"],
                    image_width=metadata["image_width"],
                    image_height=metadata["image_height"],
                    confidence_score=0.8 - (i * 0.1),  # 순서에 따라 점수 감소
                    search_query=query,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
                collected_icons.append(icon_data)
        
        return collected_icons
    
    def collect_from_github_aws_icons(self) -> List[WebIconData]:
        """GitHub의 AWS 아이콘 저장소에서 수집"""
        print("GitHub AWS 아이콘 저장소에서 수집 중...")
        
        # GitHub API를 사용한 실제 구현
        github_repos = [
            "aws/aws-icons-for-plantuml",
            "awslabs/aws-icons-for-plantuml",
            "aws-samples/aws-icons-for-plantuml"
        ]
        
        collected_icons = []
        
        for repo in github_repos:
            try:
                # GitHub API 호출 (실제 구현)
                api_url = f"https://api.github.com/repos/{repo}/contents"
                response = requests.get(api_url, headers=self.headers)
                
                if response.status_code == 200:
                    contents = response.json()
                    for item in contents:
                        if item["type"] == "file" and item["name"].lower().endswith(('.png', '.svg')):
                            # 파일 다운로드
                            download_url = item["download_url"]
                            filename = f"github_{repo.replace('/', '_')}_{item['name']}"
                            
                            metadata = self.download_image(download_url, filename)
                            if metadata:
                                service_name = self.extract_service_from_filename(item["name"])
                                icon_data = WebIconData(
                                    service_name=service_name,
                                    source_url=f"GitHub: {repo}",
                                    image_url=download_url,
                                    file_path=metadata["file_path"],
                                    file_size=metadata["file_size"],
                                    image_width=metadata["image_width"],
                                    image_height=metadata["image_height"],
                                    confidence_score=0.9,  # GitHub 소스는 높은 신뢰도
                                    search_query=f"github {repo}",
                                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                                )
                                collected_icons.append(icon_data)
                                
            except Exception as e:
                print(f"GitHub 수집 실패: {repo} - {e}")
        
        return collected_icons
    
    def extract_service_from_filename(self, filename: str) -> str:
        """파일명에서 서비스명 추출"""
        # 파일명에서 서비스명 추출 로직
        name = filename.lower()
        name = name.replace('.png', '').replace('.svg', '')
        name = name.replace('_', ' ').replace('-', ' ')
        
        # AWS 접두사 제거
        if name.startswith('aws'):
            name = name[3:].strip()
        if name.startswith('amazon'):
            name = name[6:].strip()
        
        return name.title()
    
    def collect_from_aws_official_docs(self) -> List[WebIconData]:
        """AWS 공식 문서에서 아이콘 수집"""
        print("AWS 공식 문서에서 아이콘 수집 중...")
        
        # AWS 공식 문서 URL들
        aws_doc_urls = [
            "https://docs.aws.amazon.com/",
            "https://aws.amazon.com/architecture/icons/",
            "https://aws.amazon.com/products/"
        ]
        
        collected_icons = []
        
        # 실제 구현에서는 웹 스크래핑을 통해 이미지 URL 추출
        # 여기서는 시뮬레이션
        for url in aws_doc_urls:
            try:
                # 웹 페이지 스크래핑 로직
                response = requests.get(url, headers=self.headers, timeout=10)
                # HTML 파싱하여 이미지 URL 추출
                # 실제 구현 필요
                
            except Exception as e:
                print(f"AWS 문서 수집 실패: {url} - {e}")
        
        return collected_icons
    
    def collect_all_services(self, max_per_service: int = 5) -> List[WebIconData]:
        """모든 AWS 서비스에 대해 아이콘 수집"""
        all_icons = []
        
        for service in self.aws_services:
            print(f"\n{service} 아이콘 수집 중...")
            
            queries = self.generate_search_queries(service)
            for query in queries[:3]:  # 상위 3개 쿼리만 사용
                try:
                    icons = self.collect_from_google_images(query, max_per_service)
                    all_icons.extend(icons)
                    
                    # 요청 간격 조절
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"수집 실패: {service} - {e}")
        
        return all_icons
    
    def save_collection(self, icons: List[WebIconData], output_file: str) -> None:
        """수집된 아이콘 데이터 저장"""
        output_path = self.output_dir / output_file
        
        # JSON으로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(icon) for icon in icons], f, ensure_ascii=False, indent=2)
        
        print(f"[OK] 수집된 아이콘 저장: {output_path} (총 {len(icons)}개)")
    
    def get_statistics(self, icons: List[WebIconData]) -> Dict:
        """수집된 아이콘 통계"""
        stats = {
            "total_icons": len(icons),
            "services": {},
            "sources": {},
            "file_sizes": [],
            "confidence_scores": []
        }
        
        for icon in icons:
            # 서비스별 통계
            stats["services"][icon.service_name] = stats["services"].get(icon.service_name, 0) + 1
            
            # 소스별 통계
            stats["sources"][icon.source_url] = stats["sources"].get(icon.source_url, 0) + 1
            
            # 파일 크기 통계
            stats["file_sizes"].append(icon.file_size)
            
            # 신뢰도 점수 통계
            stats["confidence_scores"].append(icon.confidence_score)
        
        # 평균 계산
        if stats["file_sizes"]:
            stats["avg_file_size"] = sum(stats["file_sizes"]) / len(stats["file_sizes"])
        if stats["confidence_scores"]:
            stats["avg_confidence"] = sum(stats["confidence_scores"]) / len(stats["confidence_scores"])
        
        return stats
    
    def filter_high_quality_icons(self, icons: List[WebIconData], 
                                 min_confidence: float = 0.7,
                                 min_size: int = 1000) -> List[WebIconData]:
        """고품질 아이콘만 필터링"""
        filtered = []
        
        for icon in icons:
            if (icon.confidence_score >= min_confidence and 
                icon.file_size >= min_size and
                icon.image_width >= 32 and icon.image_height >= 32):
                filtered.append(icon)
        
        return filtered
