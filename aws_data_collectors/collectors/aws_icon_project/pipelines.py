"""
Scrapy 파이프라인: AWS 아이콘 데이터 처리
수집된 아이콘 데이터의 검증, 필터링, 저장을 담당합니다.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any
from PIL import Image
import io
import hashlib

class AWSIconPipeline:
    """
    AWS 아이콘 데이터 처리 파이프라인
    
    수집된 아이콘 데이터를 검증하고 필터링하여 고품질 데이터만 저장합니다.
    """
    
    def __init__(self):
        self.output_dir = Path("collected_icons")
        self.output_dir.mkdir(exist_ok=True)
        
        # 수집된 아이콘 저장소
        self.collected_icons = []
        
        # 중복 제거를 위한 해시 저장소
        self.seen_hashes = set()
        
        # 품질 기준
        self.min_file_size = 1000  # 1KB
        self.min_dimensions = (32, 32)  # 최소 32x32
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_dimensions = (1024, 1024)  # 최대 1024x1024
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """아이템 처리"""
        try:
            # 이미지 검증
            if not self.validate_image(item):
                return None
            
            # 중복 검사
            if self.is_duplicate(item):
                return None
            
            # 품질 검사
            if not self.check_quality(item):
                return None
            
            # 아이콘 데이터 저장
            self.collected_icons.append(item)
            
            return item
            
        except Exception as e:
            spider.logger.error(f"아이템 처리 실패: {e}")
            return None
    
    def validate_image(self, item: Dict[str, Any]) -> bool:
        """이미지 유효성 검증"""
        try:
            # 파일 경로 확인
            file_path = Path(item.get('file_path', ''))
            if not file_path.exists():
                return False
            
            # 이미지 파일 열기
            with Image.open(file_path) as img:
                # 이미지 형식 확인
                if img.format not in ['PNG', 'JPEG', 'JPG', 'SVG']:
                    return False
                
                # RGB 모드로 변환 (SVG 제외)
                if img.format != 'SVG':
                    if img.mode not in ['RGB', 'RGBA']:
                        img = img.convert('RGB')
                
                # 메타데이터 업데이트
                item['image_width'] = img.width
                item['image_height'] = img.height
                item['image_format'] = img.format
                item['image_mode'] = img.mode
                
                return True
                
        except Exception:
            return False
    
    def is_duplicate(self, item: Dict[str, Any]) -> bool:
        """중복 이미지 검사"""
        try:
            file_path = Path(item.get('file_path', ''))
            if not file_path.exists():
                return True
            
            # 파일 해시 계산
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            if file_hash in self.seen_hashes:
                return True
            
            self.seen_hashes.add(file_hash)
            item['file_hash'] = file_hash
            
            return False
            
        except Exception:
            return True
    
    def check_quality(self, item: Dict[str, Any]) -> bool:
        """이미지 품질 검사"""
        try:
            file_size = item.get('file_size', 0)
            width = item.get('image_width', 0)
            height = item.get('image_height', 0)
            
            # 파일 크기 검사
            if file_size < self.min_file_size or file_size > self.max_file_size:
                return False
            
            # 이미지 크기 검사
            if width < self.min_dimensions[0] or height < self.min_dimensions[1]:
                return False
            
            if width > self.max_dimensions[0] or height > self.max_dimensions[1]:
                return False
            
            # 종횡비 검사 (너무 극단적인 비율 제외)
            aspect_ratio = width / height
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                return False
            
            return True
            
        except Exception:
            return False
    
    def close_spider(self, spider):
        """스파이더 종료 시 처리"""
        if self.collected_icons:
            # 고품질 아이콘만 필터링
            high_quality_icons = self.filter_high_quality_icons()
            
            # 결과 저장
            self.save_results(high_quality_icons, spider)
            
            # 통계 출력
            self.print_statistics(high_quality_icons)
    
    def filter_high_quality_icons(self) -> list:
        """고품질 아이콘 필터링"""
        filtered = []
        
        for icon in self.collected_icons:
            confidence = icon.get('confidence_score', 0)
            file_size = icon.get('file_size', 0)
            
            # 신뢰도와 파일 크기 기준
            if confidence >= 0.7 and file_size >= 2000:
                filtered.append(icon)
        
        return filtered
    
    def save_results(self, icons: list, spider):
        """결과 저장"""
        timestamp = int(time.time())
        
        # JSON 파일로 저장
        output_file = self.output_dir / f"high_quality_icons_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(icons, f, ensure_ascii=False, indent=2)
        
        # CSV 파일로도 저장
        csv_file = self.output_dir / f"high_quality_icons_{timestamp}.csv"
        self.save_as_csv(icons, csv_file)
        
        spider.logger.info(f"고품질 아이콘 {len(icons)}개 저장 완료:")
        spider.logger.info(f"  JSON: {output_file}")
        spider.logger.info(f"  CSV: {csv_file}")
    
    def save_as_csv(self, icons: list, csv_file: Path):
        """CSV 형식으로 저장"""
        import csv
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if not icons:
                return
            
            # 헤더 작성
            fieldnames = icons[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # 데이터 작성
            for icon in icons:
                writer.writerow(icon)
    
    def print_statistics(self, icons: list):
        """통계 출력"""
        if not icons:
            print("수집된 고품질 아이콘이 없습니다.")
            return
        
        # 서비스별 통계
        services = {}
        sources = {}
        file_sizes = []
        confidence_scores = []
        
        for icon in icons:
            service = icon.get('service_name', 'Unknown')
            source = icon.get('source_url', 'Unknown')
            
            services[service] = services.get(service, 0) + 1
            sources[source] = sources.get(source, 0) + 1
            file_sizes.append(icon.get('file_size', 0))
            confidence_scores.append(icon.get('confidence_score', 0))
        
        print(f"\n=== 수집 통계 ===")
        print(f"총 아이콘 수: {len(icons)}")
        print(f"평균 파일 크기: {sum(file_sizes) / len(file_sizes):.0f} bytes")
        print(f"평균 신뢰도: {sum(confidence_scores) / len(confidence_scores):.2f}")
        
        print(f"\n=== 서비스별 분포 (상위 10개) ===")
        sorted_services = sorted(services.items(), key=lambda x: x[1], reverse=True)
        for service, count in sorted_services[:10]:
            print(f"  {service}: {count}개")
        
        print(f"\n=== 소스별 분포 ===")
        for source, count in sources.items():
            print(f"  {source}: {count}개")


class ImageProcessingPipeline:
    """
    이미지 전처리 파이프라인
    
    수집된 이미지를 모델 훈련에 적합한 형태로 전처리합니다.
    """
    
    def __init__(self):
        self.processed_dir = Path("processed_icons")
        self.processed_dir.mkdir(exist_ok=True)
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """이미지 전처리"""
        try:
            file_path = Path(item.get('file_path', ''))
            if not file_path.exists():
                return item
            
            # 이미지 전처리
            processed_path = self.preprocess_image(file_path, item)
            if processed_path:
                item['processed_path'] = str(processed_path)
            
            return item
            
        except Exception as e:
            spider.logger.error(f"이미지 전처리 실패: {e}")
            return item
    
    def preprocess_image(self, file_path: Path, item: Dict[str, Any]) -> Path:
        """이미지 전처리"""
        try:
            with Image.open(file_path) as img:
                # 크기 정규화 (64x64로 리사이즈)
                target_size = (64, 64)
                img_resized = img.resize(target_size, Image.Resampling.LANCZOS)
                
                # RGB 모드로 변환
                if img_resized.mode != 'RGB':
                    img_resized = img_resized.convert('RGB')
                
                # 전처리된 파일 저장
                service_name = item.get('service_name', 'unknown').lower()
                processed_filename = f"processed_{service_name}_{file_path.stem}.png"
                processed_path = self.processed_dir / processed_filename
                
                img_resized.save(processed_path, 'PNG', optimize=True)
                
                return processed_path
                
        except Exception:
            return None
