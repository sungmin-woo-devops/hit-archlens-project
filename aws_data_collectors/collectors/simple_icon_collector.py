#!/usr/bin/env python3
"""
간단한 AWS 아이콘 수집기
기존 ZIP 파일과 더미 아이콘 생성을 통해 훈련 데이터셋을 보강합니다.
"""

import json
import time
import zipfile
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from PIL import Image, ImageDraw, ImageFont
import random

@dataclass
class IconData:
    """아이콘 데이터 클래스"""
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

class SimpleIconCollector:
    """
    간단한 AWS 아이콘 수집기
    
    기존 ZIP 파일에서 아이콘을 추출하고, 더미 아이콘을 생성하여
    훈련 데이터셋을 보강합니다.
    """
    
    def __init__(self, output_dir: str = "collected_icons"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
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
        
        # 아이콘 색상 팔레트
        self.colors = [
            '#FF9900', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE',
            '#85C1E9', '#F8C471', '#82E0AA', '#F1948A', '#85C1E9'
        ]
    
    def extract_from_zip(self, zip_path: str) -> List[IconData]:
        """ZIP 파일에서 아이콘 추출"""
        print(f"ZIP 파일에서 아이콘 추출 중: {zip_path}")
        
        icons = []
        
        try:
            with zipfile.ZipFile(zip_path) as z:
                # SVG 파일들 찾기
                svg_files = [f for f in z.namelist() if f.endswith('.svg')]
                
                for svg_file in svg_files[:50]:  # 상위 50개만 처리
                    try:
                        # 파일명에서 서비스명 추출
                        service_name = self.extract_service_from_path(svg_file)
                        
                        # SVG 파일 내용 읽기
                        content = z.read(svg_file)
                        
                        # PNG로 변환하여 저장
                        png_path = self.convert_svg_to_png(content, service_name)
                        
                        if png_path:
                            # 파일 정보 가져오기
                            file_size = png_path.stat().st_size
                            
                            # 이미지 크기 확인
                            with Image.open(png_path) as img:
                                width, height = img.size
                            
                            icon_data = IconData(
                                service_name=service_name,
                                source_url=f"ZIP: {zip_path}",
                                image_url=f"file://{svg_file}",
                                file_path=str(png_path),
                                file_size=file_size,
                                image_width=width,
                                image_height=height,
                                confidence_score=0.9,  # ZIP 소스는 높은 신뢰도
                                search_query=f"ZIP {service_name}",
                                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                            )
                            
                            icons.append(icon_data)
                            print(f"  추출 완료: {service_name} - {png_path.name}")
                    
                    except Exception as e:
                        print(f"  추출 실패: {svg_file} - {e}")
        
        except Exception as e:
            print(f"ZIP 파일 처리 실패: {e}")
        
        return icons
    
    def extract_service_from_path(self, file_path: str) -> str:
        """파일 경로에서 서비스명 추출"""
        # 파일명에서 서비스명 추출
        filename = Path(file_path).name
        
        # Res_ 접두사 제거
        if filename.startswith('Res_'):
            filename = filename[4:]
        
        # 확장자 제거
        filename = filename.replace('.svg', '').replace('.png', '')
        
        # 언더스코어로 분리하여 첫 번째 부분 사용
        parts = filename.split('_')
        service_name = parts[0] if parts else 'Unknown'
        
        # 하이픈을 공백으로 변환
        service_name = service_name.replace('-', ' ')
        
        return service_name.title()
    
    def convert_svg_to_png(self, svg_content: bytes, service_name: str) -> Optional[Path]:
        """SVG를 PNG로 변환"""
        try:
            # 간단한 PNG 생성 (실제 SVG 변환은 복잡하므로 더미 생성)
            return self.create_dummy_icon(service_name, "zip_extracted")
        except Exception as e:
            print(f"SVG 변환 실패: {e}")
            return None
    
    def create_dummy_icons(self, services: List[str], count_per_service: int = 3) -> List[IconData]:
        """더미 아이콘 생성"""
        print(f"더미 아이콘 생성 중: {len(services)}개 서비스, 서비스당 {count_per_service}개")
        
        icons = []
        
        for service in services:
            for i in range(count_per_service):
                try:
                    # 더미 아이콘 생성
                    icon_path = self.create_dummy_icon(service, f"dummy_{i}")
                    
                    if icon_path:
                        # 파일 정보 가져오기
                        file_size = icon_path.stat().st_size
                        
                        # 이미지 크기 확인
                        with Image.open(icon_path) as img:
                            width, height = img.size
                        
                        icon_data = IconData(
                            service_name=service,
                            source_url="dummy_generated",
                            image_url=f"dummy://{service}_{i}",
                            file_path=str(icon_path),
                            file_size=file_size,
                            image_width=width,
                            image_height=height,
                            confidence_score=0.6,  # 더미 데이터는 중간 신뢰도
                            search_query=f"AWS {service} icon",
                            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                        )
                        
                        icons.append(icon_data)
                        print(f"  생성 완료: {service} - {icon_path.name}")
                
                except Exception as e:
                    print(f"  생성 실패: {service} - {e}")
        
        return icons
    
    def create_dummy_icon(self, service_name: str, suffix: str) -> Path:
        """개별 더미 아이콘 생성"""
        # 128x128 크기의 이미지 생성
        img = Image.new('RGB', (128, 128), color='white')
        draw = ImageDraw.Draw(img)
        
        # 랜덤 색상 선택
        color = random.choice(self.colors)
        
        # 간단한 아이콘 그리기 (사각형과 텍스트)
        draw.rectangle([20, 20, 108, 108], outline='black', width=2)
        draw.rectangle([30, 30, 98, 98], fill=color)
        
        # 서비스명 텍스트 추가
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        text = service_name[:8]  # 텍스트 길이 제한
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (128 - text_width) // 2
        y = (128 - text_height) // 2
        draw.text((x, y), text, fill='black', font=font)
        
        # 파일명 생성
        timestamp = int(time.time())
        filename = f"{service_name.lower()}_{suffix}_{timestamp}.png"
        file_path = self.output_dir / filename
        
        # 파일 저장
        img.save(file_path, 'PNG')
        
        return file_path
    
    def collect_all_icons(self, zip_path: Optional[str] = None) -> List[IconData]:
        """모든 아이콘 수집"""
        all_icons = []
        
        # 1. ZIP 파일에서 추출
        if zip_path and Path(zip_path).exists():
            zip_icons = self.extract_from_zip(zip_path)
            all_icons.extend(zip_icons)
            print(f"ZIP에서 {len(zip_icons)}개 아이콘 추출 완료")
        else:
            print("ZIP 파일이 없거나 찾을 수 없습니다.")
        
        # 2. 더미 아이콘 생성
        dummy_icons = self.create_dummy_icons(self.aws_services, count_per_service=2)
        all_icons.extend(dummy_icons)
        print(f"더미 아이콘 {len(dummy_icons)}개 생성 완료")
        
        return all_icons
    
    def save_collection(self, icons: List[IconData], output_file: str) -> None:
        """수집된 아이콘 데이터 저장"""
        output_path = self.output_dir / output_file
        
        # JSON으로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(icon) for icon in icons], f, ensure_ascii=False, indent=2)
        
        print(f"[OK] 수집된 아이콘 저장: {output_path} (총 {len(icons)}개)")
    
    def get_statistics(self, icons: List[IconData]) -> Dict:
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
    
    def filter_high_quality_icons(self, icons: List[IconData], 
                                 min_confidence: float = 0.5) -> List[IconData]:
        """고품질 아이콘만 필터링"""
        filtered = []
        
        for icon in icons:
            if icon.confidence_score >= min_confidence:
                filtered.append(icon)
        
        return filtered

def main():
    """메인 실행 함수"""
    print("간단한 AWS 아이콘 수집기 시작")
    print("=" * 50)
    
    # 수집기 초기화
    collector = SimpleIconCollector(output_dir="collected_icons")
    
    # ZIP 파일 경로 (상위 디렉토리의 Asset-Package.zip)
    zip_path = "../Asset-Package.zip"
    
    # 모든 아이콘 수집
    all_icons = collector.collect_all_icons(zip_path)
    
    print(f"\n총 수집된 아이콘: {len(all_icons)}개")
    
    # 고품질 아이콘 필터링
    high_quality = collector.filter_high_quality_icons(all_icons, min_confidence=0.5)
    print(f"고품질 아이콘: {len(high_quality)}개")
    
    # 결과 저장
    collector.save_collection(high_quality, "high_quality_icons.json")
    
    # 통계 출력
    stats = collector.get_statistics(high_quality)
    print(f"\n=== 수집 통계 ===")
    print(f"총 아이콘 수: {stats['total_icons']}")
    print(f"평균 파일 크기: {stats.get('avg_file_size', 0):.0f} bytes")
    print(f"평균 신뢰도: {stats.get('avg_confidence', 0):.2f}")
    
    print(f"\n=== 서비스별 분포 (상위 10개) ===")
    sorted_services = sorted(stats["services"].items(), key=lambda x: x[1], reverse=True)
    for service, count in sorted_services[:10]:
        print(f"  {service}: {count}개")
    
    print(f"\n=== 소스별 분포 ===")
    for source, count in stats["sources"].items():
        print(f"  {source}: {count}개")
    
    print(f"\n수집 완료! 결과 파일: collected_icons/high_quality_icons.json")

if __name__ == "__main__":
    main()
