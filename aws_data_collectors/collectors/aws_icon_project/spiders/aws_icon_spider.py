"""
Scrapy 스파이더: AWS 아이콘 웹 수집
실제 웹 스크래핑을 통해 AWS 아이콘을 수집합니다.
"""

import scrapy
import json
import time
import re
from urllib.parse import urljoin, urlparse
from pathlib import Path
from typing import Dict, List, Optional
import requests
from PIL import Image
import io

class AWSIconSpider(scrapy.Spider):
    name = 'aws_icon_spider'
    
    def __init__(self, service_name=None, max_results=10, *args, **kwargs):
        super(AWSIconSpider, self).__init__(*args, **kwargs)
        self.service_name = service_name
        # max_results를 정수로 변환
        try:
            self.max_results = int(max_results) if max_results else 10
        except (ValueError, TypeError):
            self.max_results = 10
        
        # AWS 서비스 목록
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
        
        # 출력 디렉토리 설정
        self.output_dir = Path("collected_icons")
        self.output_dir.mkdir(exist_ok=True)
        
        # 수집된 아이콘 저장소
        self.collected_icons = []
    
    def start_requests(self):
        """스파이더 시작 요청"""
        if self.service_name:
            # 특정 서비스만 수집
            services = [self.service_name]
        else:
            # 모든 서비스 수집
            services = self.aws_services
        
        for service in services:
            queries = self.generate_search_queries(service)
            for query in queries[:3]:  # 상위 3개 쿼리만 사용
                # Google Images 검색 URL
                search_url = f"https://www.google.com/search?q={query}&tbm=isch"
                
                yield scrapy.Request(
                    url=search_url,
                    callback=self.parse_google_images,
                    meta={
                        'service_name': service,
                        'search_query': query,
                        'source': 'google_images'
                    },
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                )
    
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
    
    def parse_google_images(self, response):
        """Google Images 검색 결과 파싱"""
        service_name = response.meta['service_name']
        search_query = response.meta['search_query']
        
        # Google Images에서 이미지 URL 추출
        # 실제 구현에서는 JavaScript 렌더링이 필요할 수 있음
        image_urls = self.extract_image_urls_from_google(response)
        
        for i, image_url in enumerate(image_urls[:self.max_results]):
            yield scrapy.Request(
                url=image_url,
                callback=self.parse_image,
                meta={
                    'service_name': service_name,
                    'search_query': search_query,
                    'source': 'google_images',
                    'image_index': i
                },
                dont_filter=True
            )
    
    def extract_image_urls_from_google(self, response) -> List[str]:
        """Google Images 페이지에서 이미지 URL 추출"""
        image_urls = []
        
        # Google Images의 이미지 URL 패턴
        # 실제 구현에서는 더 정교한 파싱이 필요
        try:
            # JSON 데이터에서 이미지 URL 추출 시도
            script_tags = response.xpath('//script[contains(text(), "AF_initDataCallback")]/text()').getall()
            
            for script in script_tags:
                # 이미지 URL 패턴 찾기
                urls = re.findall(r'https://[^"\s]+\.(?:png|jpg|jpeg|svg|gif)', script)
                image_urls.extend(urls)
            
            # 대안: img 태그에서 직접 추출
            if not image_urls:
                img_tags = response.xpath('//img/@src').getall()
                image_urls = [url for url in img_tags if url.startswith('http')]
            
        except Exception as e:
            self.logger.error(f"이미지 URL 추출 실패: {e}")
        
        return list(set(image_urls))  # 중복 제거
    
    def parse_image(self, response):
        """이미지 다운로드 및 처리"""
        service_name = response.meta['service_name']
        search_query = response.meta['search_query']
        source = response.meta['source']
        image_index = response.meta.get('image_index', 0)
        
        try:
            # 이미지 검증
            img = Image.open(io.BytesIO(response.body))
            img.verify()
            
            # 다시 열어서 메타데이터 추출
            img = Image.open(io.BytesIO(response.body))
            
            # 파일명 생성
            timestamp = int(time.time())
            filename = f"{service_name.lower()}_{source}_{image_index}_{timestamp}.png"
            file_path = self.output_dir / filename
            
            # 파일 저장
            with open(file_path, 'wb') as f:
                f.write(response.body)
            
            # 아이콘 데이터 생성
            icon_data = {
                'service_name': service_name,
                'source_url': source,
                'image_url': response.url,
                'file_path': str(file_path),
                'file_size': len(response.body),
                'image_width': img.width,
                'image_height': img.height,
                'confidence_score': 0.8 - (image_index * 0.1),
                'search_query': search_query,
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.collected_icons.append(icon_data)
            
            self.logger.info(f"아이콘 수집 완료: {service_name} - {filename}")
            
        except Exception as e:
            self.logger.error(f"이미지 처리 실패: {response.url} - {e}")
    
    def closed(self, reason):
        """스파이더 종료 시 수집된 데이터 저장"""
        if self.collected_icons:
            output_file = self.output_dir / f"collected_icons_{int(time.time())}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.collected_icons, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"수집 완료: {len(self.collected_icons)}개 아이콘을 {output_file}에 저장")


class GitHubAWSIconSpider(scrapy.Spider):
    name = 'github_aws_icon_spider'
    
    def __init__(self, *args, **kwargs):
        super(GitHubAWSIconSpider, self).__init__(*args, **kwargs)
        
        # GitHub AWS 아이콘 저장소들
        self.github_repos = [
            "aws/aws-icons-for-plantuml",
            "awslabs/aws-icons-for-plantuml",
            "aws-samples/aws-icons-for-plantuml"
        ]
        
        self.output_dir = Path("collected_icons")
        self.output_dir.mkdir(exist_ok=True)
        self.collected_icons = []
    
    def start_requests(self):
        """GitHub 저장소에서 아이콘 수집 시작"""
        for repo in self.github_repos:
            # GitHub API를 통해 저장소 내용 조회
            api_url = f"https://api.github.com/repos/{repo}/contents"
            
            yield scrapy.Request(
                url=api_url,
                callback=self.parse_github_repo,
                meta={'repo': repo},
                headers={
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
    
    def parse_github_repo(self, response):
        """GitHub 저장소 내용 파싱"""
        repo = response.meta['repo']
        
        try:
            contents = json.loads(response.text)
            
            for item in contents:
                if item['type'] == 'file' and item['name'].lower().endswith(('.png', '.svg')):
                    # 파일 다운로드
                    download_url = item['download_url']
                    
                    yield scrapy.Request(
                        url=download_url,
                        callback=self.parse_github_file,
                        meta={
                            'repo': repo,
                            'filename': item['name'],
                            'download_url': download_url
                        },
                        dont_filter=True
                    )
                    
        except Exception as e:
            self.logger.error(f"GitHub 저장소 파싱 실패: {repo} - {e}")
    
    def parse_github_file(self, response):
        """GitHub 파일 다운로드 및 처리"""
        repo = response.meta['repo']
        filename = response.meta['filename']
        download_url = response.meta['download_url']
        
        try:
            # 이미지 검증
            img = Image.open(io.BytesIO(response.body))
            img.verify()
            
            # 다시 열어서 메타데이터 추출
            img = Image.open(io.BytesIO(response.body))
            
            # 파일명 생성
            safe_repo_name = repo.replace('/', '_')
            new_filename = f"github_{safe_repo_name}_{filename}"
            file_path = self.output_dir / new_filename
            
            # 파일 저장
            with open(file_path, 'wb') as f:
                f.write(response.body)
            
            # 서비스명 추출
            service_name = self.extract_service_from_filename(filename)
            
            # 아이콘 데이터 생성
            icon_data = {
                'service_name': service_name,
                'source_url': f"GitHub: {repo}",
                'image_url': download_url,
                'file_path': str(file_path),
                'file_size': len(response.body),
                'image_width': img.width,
                'image_height': img.height,
                'confidence_score': 0.9,  # GitHub 소스는 높은 신뢰도
                'search_query': f"github {repo}",
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.collected_icons.append(icon_data)
            
            self.logger.info(f"GitHub 아이콘 수집 완료: {service_name} - {new_filename}")
            
        except Exception as e:
            self.logger.error(f"GitHub 파일 처리 실패: {download_url} - {e}")
    
    def extract_service_from_filename(self, filename: str) -> str:
        """파일명에서 서비스명 추출"""
        name = filename.lower()
        name = name.replace('.png', '').replace('.svg', '')
        name = name.replace('_', ' ').replace('-', ' ')
        
        # AWS 접두사 제거
        if name.startswith('aws'):
            name = name[3:].strip()
        if name.startswith('amazon'):
            name = name[6:].strip()
        
        return name.title()
    
    def closed(self, reason):
        """스파이더 종료 시 수집된 데이터 저장"""
        if self.collected_icons:
            output_file = self.output_dir / f"github_icons_{int(time.time())}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.collected_icons, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"GitHub 수집 완료: {len(self.collected_icons)}개 아이콘을 {output_file}에 저장")
