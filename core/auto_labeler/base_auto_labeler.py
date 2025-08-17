"""
Base Auto Labeler Module

클라우드 아키텍처 다이어그램 자동 라벨링을 위한 추상 베이스 클래스
"""

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed # ThreadPoolExecutor 임포트
from tqdm import tqdm

from ..models import (
    DetectionResult, 
    AnalysisResult, 
    BatchAnalysisResult,
    CloudProvider,
    AnalysisMethod,
    BoundingBox
)


class BaseAutoLabeler(ABC):
    """
    클라우드 중립 오토라벨러 기본 클래스
    
    모든 클라우드 제공자별 오토라벨러가 상속받아야 하는 기본 클래스입니다.
    """
    
    def __init__(self, cloud_provider: Union[CloudProvider, str], config: Dict[str, Any]):
        """
        기본 오토라벨러 초기화
        
        Args:
            cloud_provider: 클라우드 제공자 (aws, gcp, azure, naver)
            config: 설정 딕셔너리
        """
        self.cloud_provider = CloudProvider(cloud_provider) if isinstance(cloud_provider, str) else cloud_provider
        self.config = config
        self.taxonomy = self._load_taxonomy()
        
        # 초기화 로그
        print(f"✅ {self.cloud_provider.value.upper()} 오토라벨러 초기화 완료")
        print(f"   - 제공자: {self.cloud_provider.value}")
        print(f"   - 방법: {self.get_method_name()}")
    
    @abstractmethod
    def get_method_name(self) -> str:
        """분석 방법 이름 반환 (cv, llm, hybrid)"""
        pass
    
    @abstractmethod
    def _load_taxonomy(self):
        """택소노미 로드 (클라우드별 구현)"""
        pass
    
    @abstractmethod
    def _analyze_single_image(self, image: Image.Image) -> List[DetectionResult]:
        """단일 이미지 분석 (클라우드별 구현)"""
        pass
    
    def analyze_image(self, image_path: Union[str, Path]) -> AnalysisResult:
        """
        단일 이미지를 분석하여 서비스 아이콘을 감지하고 라벨링합니다.
        
        Args:
            image_path: 분석할 이미지 파일 경로
            
        Returns:
            AnalysisResult: 분석 결과
        """
        start_time = time.time()
        image_path = Path(image_path)
        
        if not image_path.exists():
            print(f"❌ 이미지 파일을 찾을 수 없습니다: {image_path}")
            return AnalysisResult(
                image_path=image_path,
                width=0, height=0, detections=[], processing_time=0.0,
                cloud_provider=self.cloud_provider,
                analysis_method=self.get_method_name(),
                success=False, errors=[f"Image file not found: {image_path}"] # Set success to False
            )

        try:
            image = Image.open(image_path).convert("RGB")
            
            # 실제 분석 로직
            detections = self._analyze_single_image(image)
            
            # 택소노미 정규화
            normalized_detections = self._normalize_detections(detections)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"✅ 이미지 분석 완료: {image_path.name} - {len(normalized_detections)}개 감지 ({processing_time:.2f}초)")
            
            return AnalysisResult(
                image_path=image_path,
                width=image.width,
                height=image.height,
                detections=normalized_detections,
                processing_time=processing_time,
                cloud_provider=self.cloud_provider,
                analysis_method=self.get_method_name(),
                success=True # Set success to True
            )
        except Exception as e:
            print(f"❌ 이미지 분석 실패: {image_path.name} - {e}")
            return AnalysisResult(
                image_path=image_path,
                width=0, height=0, detections=[], processing_time=time.time() - start_time,
                cloud_provider=self.cloud_provider,
                analysis_method=self.get_method_name(),
                success=False, errors=[str(e)] # Set success to False and record error
            )

    def analyze_batch(self, image_paths: List[Union[str, Path]]) -> BatchAnalysisResult:
        """
        여러 이미지를 배치로 분석합니다.
        
        Args:
            image_paths: 분석할 이미지 파일 경로 리스트
            
        Returns:
            BatchAnalysisResult: 배치 분석 결과
        """
        print(f"📊 배치 분석 시작: {len(image_paths)}개 이미지")
        total_start_time = time.time()
        
        all_results: List[AnalysisResult] = []
        total_detections = 0
        successful_images = 0
        failed_images = 0
        total_processing_time = 0.0
        batch_errors: List[Dict[str, Any]] = []

        # 병렬 처리 설정
        max_workers = self.config.get("performance", {}).get("max_workers", 4)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {executor.submit(self.analyze_image, path): path for path in image_paths}
            
            for future in tqdm(as_completed(future_to_path), total=len(image_paths), desc="이미지 분석"):
                image_path = future_to_path[future]
                try:
                    result = future.result()
                    all_results.append(result)
                    total_processing_time += result.processing_time
                    if result.success:
                        successful_images += 1
                        total_detections += result.detection_count
                    else:
                        failed_images += 1
                        batch_errors.append({"image_path": str(image_path), "message": result.errors[0] if result.errors else "Unknown error"})
                except Exception as e:
                    failed_images += 1
                    batch_errors.append({"image_path": str(image_path), "message": str(e)})
                    print(f"❌ 배치 분석 중 오류 발생: {image_path.name} - {e}")
        
        total_end_time = time.time()
        total_batch_processing_time = total_end_time - total_start_time
        
        print(f"✅ 배치 분석 완료: {successful_images}개 성공, {failed_images}개 실패 ({total_batch_processing_time:.2f}초)")
        
        return BatchAnalysisResult(
            results=all_results,
            total_images=len(image_paths),
            total_detections=total_detections,
            total_processing_time=total_processing_time, # Add total_processing_time
            average_processing_time=total_processing_time / successful_images if successful_images > 0 else 0.0,
            success_count=successful_images,
            error_count=failed_images,
            errors=batch_errors # Pass batch_errors here
        )
    
    def analyze_directory(self, directory_path: Union[str, Path], 
                         file_extensions: Optional[List[str]] = None) -> BatchAnalysisResult:
        """
        디렉터리 내 모든 이미지 분석
        
        Args:
            directory_path: 분석할 디렉터리 경로
            file_extensions: 지원할 파일 확장자 목록 (기본값: ['.png', '.jpg', '.jpeg'])
            
        Returns:
            BatchAnalysisResult: 배치 분석 결과
        """
        if file_extensions is None:
            file_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
        
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"유효하지 않은 디렉터리: {directory_path}")
        
        # 지원되는 확장자를 가진 이미지 파일들 찾기
        image_paths = []
        for ext in file_extensions:
            image_paths.extend(directory.glob(f"*{ext}"))
            image_paths.extend(directory.glob(f"*{ext.upper()}"))
        
        if not image_paths:
            print(f"⚠️ 디렉터리에서 이미지 파일을 찾을 수 없습니다: {directory_path}")
            return BatchAnalysisResult(
                results=[],
                total_images=0,
                total_detections=0,
                total_processing_time=0.0,
                average_processing_time=0.0,
                success_count=0,
                error_count=0,
                errors=[]
            )
        
        print(f" {len(image_paths)}개 이미지 파일 발견: {directory_path}")
        return self.analyze_batch(image_paths)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        오토라벨러 통계 정보 반환
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        return {
            "cloud_provider": self.cloud_provider.value,
            "method": self.get_method_name(),
            "taxonomy_loaded": self.taxonomy is not None,
            "config": self.config
        }
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        설정 유효성 검증
        
        Returns:
            Tuple[bool, List[str]]: (유효성 여부, 오류 메시지 목록)
        """
        errors = []
        
        # 기본 검증
        if not self.config:
            errors.append("설정이 비어있습니다")
        
        # 클라우드 제공자별 검증
        if self.cloud_provider == CloudProvider.AWS:
            if "taxonomy_csv" not in self.config.get("data", {}):
                errors.append("AWS 택소노미 CSV 경로가 설정되지 않았습니다")
        
        return len(errors) == 0, errors

    def _normalize_detections(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """택소노미를 사용하여 감지 결과를 정규화"""
        if not self.taxonomy:
            return detections # 택소노미가 없으면 정규화하지 않음

        normalized_results = []
        for det in detections:
            taxonomy_result = self.taxonomy.normalize(det.label)
            det.canonical_name = taxonomy_result.canonical_name
            # 신뢰도 융합 (원래 감지 신뢰도와 택소노미 신뢰도)
            det.confidence = det.confidence * taxonomy_result.confidence
            
            # 서비스 코드 추론 (선택적)
            if hasattr(self, 'service_code_mapping') and det.canonical_name:
                det.service_code = self.service_code_mapping.get(det.canonical_name, None)
            
            normalized_results.append(det)
        return normalized_results
