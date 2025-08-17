"""
Hybrid Auto Labeler Module

Computer Vision과 LLM을 결합한 하이브리드 오토라벨링을 위한 베이스 클래스
"""

import time
from typing import List, Dict, Any, Optional, Tuple, Union
from PIL import Image
from abc import abstractmethod

from .base_auto_labeler import BaseAutoLabeler
from .cv_auto_labeler import CVAutoLabeler
from .llm_auto_labeler import LLMAutoLabeler
from ..models import (
    DetectionResult, 
    AnalysisResult, 
    BoundingBox,
    CloudProvider,
    AnalysisMethod,
    DetectionStatus
)


class HybridAutoLabeler(BaseAutoLabeler):
    """
    하이브리드 오토라벨러 베이스 클래스
    
    Computer Vision과 LLM을 결합하여 더 정확한 아키텍처 분석을 수행합니다.
    """
    
    def __init__(self, cloud_provider: Union[CloudProvider, str], config: Dict[str, Any]):
        """
        하이브리드 오토라벨러 초기화
        
        Args:
            cloud_provider: 클라우드 제공자
            config: 설정 딕셔너리
        """
        # 하이브리드 설정
        self.hybrid_config = config.get("hybrid", {})
        self.cv_weight = self.hybrid_config.get("cv_weight", 0.6)
        self.llm_weight = self.hybrid_config.get("llm_weight", 0.4)
        self.fusion_method = self.hybrid_config.get("fusion_method", "weighted")
        self.iou_threshold = self.hybrid_config.get("iou_threshold", 0.5)
        self.confidence_threshold = self.hybrid_config.get("confidence_threshold", 0.3)
        
        # CV와 LLM 오토라벨러는 이미 초기화되어 있음 (하위 클래스에서)
        # self.cv_labeler = self._create_cv_labeler(cloud_provider, config)
        # self.llm_labeler = self._create_llm_labeler(cloud_provider, config)
        
        # 부모 클래스 초기화 (taxonomy 로드 포함)
        super().__init__(cloud_provider, config)
        
        print(f"   - CV 가중치: {self.cv_weight}")
        print(f"   - LLM 가중치: {self.llm_weight}")
        print(f"   - 융합 방법: {self.fusion_method}")
        print(f"   - IoU 임계값: {self.iou_threshold}")
    
    def get_method_name(self) -> str:
        """분석 방법 이름"""
        return "hybrid"
    
    @abstractmethod
    def _create_cv_labeler(self, cloud_provider: Union[CloudProvider, str], 
                          config: Dict[str, Any]) -> CVAutoLabeler:
        """CV 오토라벨러 생성 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def _create_llm_labeler(self, cloud_provider: Union[CloudProvider, str], 
                           config: Dict[str, Any]) -> LLMAutoLabeler:
        """LLM 오토라벨러 생성 (하위 클래스에서 구현)"""
        pass
    
    def _load_taxonomy(self):
        """택소노미 로드"""
        # CV 오토라벨러의 택소노미 사용
        return self.cv_labeler.taxonomy
    
    def _analyze_single_image(self, image: Image.Image) -> List[DetectionResult]:
        """단일 이미지 분석 (하이브리드)"""
        # 1. CV 분석 수행
        cv_start_time = time.time()
        cv_detections = self.cv_labeler._analyze_single_image(image)
        cv_time = time.time() - cv_start_time
        
        # 2. LLM 분석 수행
        llm_start_time = time.time()
        llm_detections = self.llm_labeler._analyze_single_image(image)
        llm_time = time.time() - llm_start_time
        
        print(f"   - CV 분석: {len(cv_detections)}개 감지, {cv_time:.2f}초")
        print(f"   - LLM 분석: {len(llm_detections)}개 감지, {llm_time:.2f}초")
        
        # 3. 결과 융합
        fused_detections = self._fuse_detections(cv_detections, llm_detections)
        
        print(f"   - 융합 결과: {len(fused_detections)}개 감지")
        
        return fused_detections
    
    def _fuse_detections(self, cv_detections: List[DetectionResult], 
                        llm_detections: List[DetectionResult]) -> List[DetectionResult]:
        """CV와 LLM 감지 결과 융합"""
        if self.fusion_method == "weighted":
            return self._weighted_fusion(cv_detections, llm_detections)
        elif self.fusion_method == "ensemble":
            return self._ensemble_fusion(cv_detections, llm_detections)
        elif self.fusion_method == "confidence":
            return self._confidence_fusion(cv_detections, llm_detections)
        elif self.fusion_method == "iou_based":
            return self._iou_based_fusion(cv_detections, llm_detections)
        else:
            # 기본적으로 가중치 융합 사용
            return self._weighted_fusion(cv_detections, llm_detections)
    
    def _weighted_fusion(self, cv_detections: List[DetectionResult], 
                        llm_detections: List[DetectionResult]) -> List[DetectionResult]:
        """가중치 기반 융합"""
        fused_detections = []
        
        # 모든 감지 결과 수집
        all_detections = []
        
        # CV 감지 결과에 가중치 적용
        for detection in cv_detections:
            weighted_confidence = detection.confidence * self.cv_weight
            weighted_detection = DetectionResult(
                bbox=detection.bbox,
                label=detection.label,
                confidence=weighted_confidence,
                service_code=detection.service_code,
                cloud_provider=detection.cloud_provider,
                status=detection.status,
                metadata={**detection.metadata, "source": "cv", "weight": self.cv_weight}
            )
            all_detections.append(weighted_detection)
        
        # LLM 감지 결과에 가중치 적용
        for detection in llm_detections:
            weighted_confidence = detection.confidence * self.llm_weight
            weighted_detection = DetectionResult(
                bbox=detection.bbox,
                label=detection.label,
                confidence=weighted_confidence,
                service_code=detection.service_code,
                cloud_provider=detection.cloud_provider,
                status=detection.status,
                metadata={**detection.metadata, "source": "llm", "weight": self.llm_weight}
            )
            all_detections.append(weighted_detection)
        
        # 중복 제거 및 신뢰도 임계값 적용
        fused_detections = self._remove_duplicates_and_filter(all_detections)
        
        return fused_detections
    
    def _ensemble_fusion(self, cv_detections: List[DetectionResult], 
                        llm_detections: List[DetectionResult]) -> List[DetectionResult]:
        """앙상블 기반 융합"""
        fused_detections = []
        
        # 모든 감지 결과를 그룹화
        detection_groups = self._group_detections_by_iou(cv_detections + llm_detections)
        
        for group in detection_groups:
            if len(group) == 0:
                continue
            
            # 그룹 내 최고 신뢰도 감지 결과 선택
            best_detection = max(group, key=lambda x: x.confidence)
            
            # 앙상블 신뢰도 계산
            ensemble_confidence = self._calculate_ensemble_confidence(group)
            
            # 최종 감지 결과 생성
            final_detection = DetectionResult(
                bbox=best_detection.bbox,
                label=best_detection.label,
                confidence=ensemble_confidence,
                service_code=best_detection.service_code,
                cloud_provider=best_detection.cloud_provider,
                status=best_detection.status,
                metadata={
                    **best_detection.metadata,
                    "ensemble_size": len(group),
                    "fusion_method": "ensemble"
                }
            )
            
            if ensemble_confidence >= self.confidence_threshold:
                fused_detections.append(final_detection)
        
        return fused_detections
    
    def _confidence_fusion(self, cv_detections: List[DetectionResult], 
                          llm_detections: List[DetectionResult]) -> List[DetectionResult]:
        """신뢰도 기반 융합"""
        fused_detections = []
        
        # 모든 감지 결과 수집
        all_detections = cv_detections + llm_detections
        
        # 신뢰도 순으로 정렬
        all_detections.sort(key=lambda x: x.confidence, reverse=True)
        
        # 중복 제거 및 신뢰도 임계값 적용
        fused_detections = self._remove_duplicates_and_filter(all_detections)
        
        return fused_detections
    
    def _iou_based_fusion(self, cv_detections: List[DetectionResult], 
                         llm_detections: List[DetectionResult]) -> List[DetectionResult]:
        """IoU 기반 융합"""
        fused_detections = []
        
        # CV와 LLM 감지 결과 매칭
        matched_pairs = self._match_detections_by_iou(cv_detections, llm_detections)
        
        # 매칭된 쌍 처리
        for cv_det, llm_det in matched_pairs:
            if cv_det and llm_det:
                # 두 감지 결과가 모두 있는 경우 - 융합
                fused_detection = self._fuse_matched_detections(cv_det, llm_det)
                fused_detections.append(fused_detection)
            elif cv_det:
                # CV만 있는 경우
                fused_detections.append(cv_det)
            elif llm_det:
                # LLM만 있는 경우
                fused_detections.append(llm_det)
        
        # 매칭되지 않은 감지 결과 추가
        unmatched_cv = [det for det in cv_detections if not any(cv_det == det for cv_det, _ in matched_pairs)]
        unmatched_llm = [det for det in llm_detections if not any(llm_det == det for _, llm_det in matched_pairs)]
        
        fused_detections.extend(unmatched_cv)
        fused_detections.extend(unmatched_llm)
        
        # 신뢰도 임계값 적용
        fused_detections = [det for det in fused_detections if det.confidence >= self.confidence_threshold]
        
        return fused_detections
    
    def _group_detections_by_iou(self, detections: List[DetectionResult]) -> List[List[DetectionResult]]:
        """IoU 기반으로 감지 결과 그룹화"""
        groups = []
        used = set()
        
        for i, detection in enumerate(detections):
            if i in used:
                continue
            
            group = [detection]
            used.add(i)
            
            for j, other_detection in enumerate(detections):
                if j in used:
                    continue
                
                if detection.bbox.iou(other_detection.bbox) >= self.iou_threshold:
                    group.append(other_detection)
                    used.add(j)
            
            groups.append(group)
        
        return groups
    
    def _match_detections_by_iou(self, cv_detections: List[DetectionResult], 
                                llm_detections: List[DetectionResult]) -> List[Tuple[Optional[DetectionResult], Optional[DetectionResult]]]:
        """IoU 기반으로 감지 결과 매칭"""
        matches = []
        cv_used = set()
        llm_used = set()
        
        for i, cv_det in enumerate(cv_detections):
            best_match = None
            best_iou = 0
            best_j = -1
            
            for j, llm_det in enumerate(llm_detections):
                if j in llm_used:
                    continue
                
                iou = cv_det.bbox.iou(llm_det.bbox)
                if iou >= self.iou_threshold and iou > best_iou:
                    best_match = llm_det
                    best_iou = iou
                    best_j = j
            
            if best_match:
                matches.append((cv_det, best_match))
                cv_used.add(i)
                llm_used.add(best_j)
            else:
                matches.append((cv_det, None))
        
        # 매칭되지 않은 LLM 감지 결과 추가
        for j, llm_det in enumerate(llm_detections):
            if j not in llm_used:
                matches.append((None, llm_det))
        
        return matches
    
    def _fuse_matched_detections(self, cv_detection: DetectionResult, 
                                llm_detection: DetectionResult) -> DetectionResult:
        """매칭된 감지 결과 융합"""
        # 바운딩 박스 융합 (가중 평균)
        cv_bbox = cv_detection.bbox
        llm_bbox = llm_detection.bbox
        
        fused_x = int((cv_bbox.x * self.cv_weight + llm_bbox.x * self.llm_weight))
        fused_y = int((cv_bbox.y * self.cv_weight + llm_bbox.y * self.llm_weight))
        fused_w = int((cv_bbox.width * self.cv_weight + llm_bbox.width * self.llm_weight))
        fused_h = int((cv_bbox.height * self.cv_weight + llm_bbox.height * self.llm_weight))
        
        fused_bbox = BoundingBox(fused_x, fused_y, fused_w, fused_h)
        
        # 라벨 선택 (더 높은 신뢰도 선택)
        if cv_detection.confidence > llm_detection.confidence:
            label = cv_detection.label
            service_code = cv_detection.service_code
        else:
            label = llm_detection.label
            service_code = llm_detection.service_code
        
        # 신뢰도 융합
        fused_confidence = (cv_detection.confidence * self.cv_weight + 
                          llm_detection.confidence * self.llm_weight)
        
        return DetectionResult(
            bbox=fused_bbox,
            label=label,
            confidence=fused_confidence,
            service_code=service_code,
            cloud_provider=self.cloud_provider,
            status=DetectionStatus.DETECTED,
            metadata={
                "fusion_method": "iou_based",
                "cv_confidence": cv_detection.confidence,
                "llm_confidence": llm_detection.confection,
                "cv_weight": self.cv_weight,
                "llm_weight": self.llm_weight
            }
        )
    
    def _calculate_ensemble_confidence(self, detections: List[DetectionResult]) -> float:
        """앙상블 신뢰도 계산"""
        if not detections:
            return 0.0
        
        # 가중 평균 신뢰도
        total_weight = 0
        weighted_sum = 0
        
        for detection in detections:
            weight = detection.metadata.get("weight", 1.0)
            total_weight += weight
            weighted_sum += detection.confidence * weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _remove_duplicates_and_filter(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """중복 제거 및 필터링"""
        filtered_detections = []
        
        for detection in detections:
            # 신뢰도 임계값 확인
            if detection.confidence < self.confidence_threshold:
                continue
            
            # 중복 확인
            is_duplicate = False
            for existing in filtered_detections:
                if detection.bbox.iou(existing.bbox) >= self.iou_threshold:
                    # 중복 발견 - 더 높은 신뢰도 선택
                    if detection.confidence > existing.confidence:
                        filtered_detections.remove(existing)
                        filtered_detections.append(detection)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered_detections.append(detection)
        
        return filtered_detections
    
    def get_hybrid_statistics(self) -> Dict[str, Any]:
        """
        하이브리드 특화 통계 정보
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        return {
            **self.get_statistics(),
            "hybrid_method": "cv_llm_fusion",
            "cv_weight": self.cv_weight,
            "llm_weight": self.llm_weight,
            "fusion_method": self.fusion_method,
            "iou_threshold": self.iou_threshold,
            "confidence_threshold": self.confidence_threshold
        }
