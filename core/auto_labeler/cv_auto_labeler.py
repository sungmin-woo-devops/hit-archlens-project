"""
Computer Vision Auto Labeler Module

Computer Vision 기반 오토라벨링을 위한 베이스 클래스
"""

import time
import cv2
import numpy as np
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from PIL import Image

from .base_auto_labeler import BaseAutoLabeler
from ..models import (
    DetectionResult, 
    AnalysisResult, 
    BoundingBox,
    CloudProvider,
    AnalysisMethod,
    DetectionStatus
)


class CVAutoLabeler(BaseAutoLabeler):
    """
    Computer Vision 기반 오토라벨러 베이스 클래스
    
    모든 CV 기반 오토라벨러가 상속해야 하는 클래스
    """
    
    def __init__(self, cloud_provider: Union[CloudProvider, str], config: Dict[str, Any]):
        """
        Computer Vision 오토라벨러 초기화
        
        Args:
            cloud_provider: 클라우드 제공자
            config: 설정 딕셔너리
        """
        # CV 설정
        self.cv_config = config.get("cv", {})
        self.detection_config = config.get("detection", {})
        self.retrieval_config = config.get("retrieval", {})
        
        # 부모 클래스 초기화 (taxonomy 로드 포함)
        super().__init__(cloud_provider, config)
        
        # CV 컴포넌트 설정
        self._setup_cv_components()
        
        print(f"   - CLIP 모델: {self.cv_config.get('clip_name', 'Not set')}")
        print(f"   - 디바이스: {self.cv_config.get('device', 'Not set')}")
        print(f"   - 감지 방법: Canny, MSER, Sliding Window")
    
    def get_method_name(self) -> str:
        """분석 방법 이름"""
        return "cv"
    
    @abstractmethod
    def _setup_cv_components(self):
        """CV 컴포넌트 설정 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def _detect_regions(self, image: Image.Image) -> List[BoundingBox]:
        """이미지에서 관심 영역 감지 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def _extract_features(self, image: Image.Image, bbox: BoundingBox) -> np.ndarray:
        """영역에서 특징 추출 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def _match_features(self, features: np.ndarray) -> List[Tuple[str, float]]:
        """특징 매칭 (하위 클래스에서 구현)"""
        pass
    
    def _analyze_single_image(self, image: Image.Image) -> List[DetectionResult]:
        """
        단일 이미지 분석 (CV 파이프라인)
        
        Args:
            image: 분석할 이미지
            
        Returns:
            List[DetectionResult]: 감지 결과 목록
        """
        detections = []
        
        # 1. 관심 영역 감지
        regions = self._detect_regions(image)
        
        # 2. 각 영역 분석
        for bbox in regions:
            try:
                # 특징 추출
                features = self._extract_features(image, bbox)
                
                # 특징 매칭
                matches = self._match_features(features)
                
                # 최고 매칭 결과 선택
                if matches:
                    best_match, confidence = matches[0]
                    
                    # 신뢰도 임계값 확인
                    if confidence >= self.retrieval_config.get("accept_score", 0.5):
                        detection = DetectionResult(
                            bbox=bbox,
                            label=best_match,
                            confidence=confidence,
                            cloud_provider=self.cloud_provider,
                            status=DetectionStatus.DETECTED
                        )
                        detections.append(detection)
                
            except Exception as e:
                print(f"⚠️ 영역 분석 실패: {e}")
                continue
        
        # 3. NMS 적용 (중복 제거)
        detections = self._apply_nms(detections)
        
        return detections
    
    def _apply_nms(self, detections: List[DetectionResult], iou_threshold: float = 0.45) -> List[DetectionResult]:
        """
        Non-Maximum Suppression 적용
        
        Args:
            detections: 감지 결과 목록
            iou_threshold: IoU 임계값
            
        Returns:
            List[DetectionResult]: NMS 적용된 결과
        """
        if not detections:
            return []
        
        # 신뢰도 순으로 정렬
        sorted_detections = sorted(detections, key=lambda x: x.confidence, reverse=True)
        
        kept_detections = []
        
        while sorted_detections:
            # 가장 높은 신뢰도의 감지 결과 선택
            current = sorted_detections.pop(0)
            kept_detections.append(current)
            
            # 나머지와 IoU 계산하여 중복 제거
            remaining = []
            for detection in sorted_detections:
                iou = current.bbox.iou(detection.bbox)
                if iou < iou_threshold:
                    remaining.append(detection)
            
            sorted_detections = remaining
        
        return kept_detections
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        이미지 전처리
        
        Args:
            image: 원본 이미지
            
        Returns:
            Image.Image: 전처리된 이미지
        """
        # 크기 조정
        max_size = self.detection_config.get("max_size", 1600)
        width, height = image.size
        
        if max(width, height) > max_size:
            scale = max_size / max(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def _crop_image(self, image: Image.Image, bbox: BoundingBox) -> Image.Image:
        """
        이미지 크롭
        
        Args:
            image: 원본 이미지
            bbox: 바운딩 박스
            
        Returns:
            Image.Image: 크롭된 이미지
        """
        return image.crop(bbox.to_xyxy())
    
    def get_cv_statistics(self) -> Dict[str, Any]:
        """
        CV 특화 통계 정보
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        return {
            **self.get_statistics(),
            "cv_method": "computer_vision",
            "detection_config": self.detection_config,
            "retrieval_config": self.retrieval_config
        }
