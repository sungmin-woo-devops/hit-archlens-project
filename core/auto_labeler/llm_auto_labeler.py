"""
LLM Auto Labeler Module

Large Language Model 기반 오토라벨링을 위한 베이스 클래스
"""

import time
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
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


class LLMAutoLabeler(BaseAutoLabeler):
    """
    Large Language Model 기반 오토라벨러 베이스 클래스
    
    모든 LLM 기반 오토라벨러가 상속해야 하는 클래스
    """
    
    def __init__(self, cloud_provider: Union[CloudProvider, str], config: Dict[str, Any]):
        """
        초기화
        
        Args:
            cloud_provider: 클라우드 제공자
            config: 설정 딕셔너리
        """
        super().__init__(cloud_provider, config)
        
        # LLM 특화 설정
        self.llm_config = config.get("llm", {})
        self.prompt_config = config.get("prompt", {})
        self.runtime_config = config.get("runtime", {})
        
        # LLM 컴포넌트 초기화
        self._setup_llm_components()
    
    def get_method_name(self) -> str:
        """분석 방법 이름"""
        return "llm"
    
    @abstractmethod
    def _setup_llm_components(self):
        """LLM 컴포넌트 설정 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def _get_llm_provider(self):
        """LLM 제공자 반환 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def _generate_prompt(self, image: Image.Image, mode: str = "full") -> str:
        """프롬프트 생성 (하위 클래스에서 구현)"""
        pass
    
    def _analyze_single_image(self, image: Image.Image) -> List[DetectionResult]:
        """
        단일 이미지 분석 (LLM 파이프라인)
        
        Args:
            image: 분석할 이미지
            
        Returns:
            List[DetectionResult]: 감지 결과 목록
        """
        detections = []
        
        # 분석 모드 결정
        mode = self.runtime_config.get("mode", "full_image")
        
        if mode == "full_image":
            # 전체 이미지 분석
            detections = self._analyze_full_image(image)
        elif mode == "patch":
            # 패치별 분석
            detections = self._analyze_patch_llm(image)
        else:
            # 하이브리드 분석
            full_detections = self._analyze_full_image(image)
            patch_detections = self._analyze_patch_llm(image)
            detections = self._merge_detections(full_detections, patch_detections)
        
        return detections
    
    def _analyze_full_image(self, image: Image.Image) -> List[DetectionResult]:
        """전체 이미지 LLM 분석"""
        try:
            # 프롬프트 생성
            prompt = self._generate_prompt(image, mode="full")
            
            # LLM 분석
            llm_provider = self._get_llm_provider()
            response = llm_provider.analyze_image(image, prompt)
            
            # 응답 파싱
            data = self._safe_json_parse(response)
            
            # 감지 결과 변환
            detections = self._parse_llm_response(data, image.size)
            
            return detections
            
        except Exception as e:
            print(f"⚠️ 전체 이미지 분석 실패: {e}")
            return []
    
    def _analyze_patch_llm(self, image: Image.Image) -> List[DetectionResult]:
        """패치별 LLM 분석"""
        try:
            # 이미지 패치 생성
            patches = self._generate_patches(image)
            
            all_detections = []
            
            for patch_info in patches:
                patch_image, bbox = patch_info
                
                # 패치 분석
                prompt = self._generate_prompt(patch_image, mode="patch")
                llm_provider = self._get_llm_provider()
                response = llm_provider.analyze_image(patch_image, prompt)
                
                # 응답 파싱
                data = self._safe_json_parse(response)
                
                # 감지 결과 변환 (좌표 조정)
                patch_detections = self._parse_llm_response(data, patch_image.size, bbox)
                all_detections.extend(patch_detections)
            
            return all_detections
            
        except Exception as e:
            print(f"⚠️ 패치 분석 실패: {e}")
            return []
    
    def _generate_patches(self, image: Image.Image) -> List[tuple]:
        """이미지 패치 생성"""
        patches = []
        
        width, height = image.size
        patch_size = self.runtime_config.get("patch_size", 512)
        stride = self.runtime_config.get("patch_stride", 256)
        
        for y in range(0, height, stride):
            for x in range(0, width, stride):
                # 패치 좌표 계산
                patch_x = x
                patch_y = y
                patch_w = min(patch_size, width - x)
                patch_h = min(patch_size, height - y)
                
                # 패치 이미지 크롭
                patch_image = image.crop((patch_x, patch_y, patch_x + patch_w, patch_y + patch_h))
                
                # 원본 좌표 정보와 함께 저장
                patches.append((patch_image, BoundingBox(patch_x, patch_y, patch_w, patch_h)))
        
        return patches
    
    def _merge_detections(self, full_detections: List[DetectionResult], 
                         patch_detections: List[DetectionResult]) -> List[DetectionResult]:
        """감지 결과 병합"""
        all_detections = full_detections + patch_detections
        
        # 중복 제거 (IoU 기반)
        merged_detections = []
        
        for detection in all_detections:
            is_duplicate = False
            
            for existing in merged_detections:
                if detection.bbox.iou(existing.bbox) > 0.5:
                    # 중복 발견 - 더 높은 신뢰도 선택
                    if detection.confidence > existing.confidence:
                        merged_detections.remove(existing)
                        merged_detections.append(detection)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                merged_detections.append(detection)
        
        return merged_detections
    
    def _safe_json_parse(self, response: str) -> Dict[str, Any]:
        """안전한 JSON 파싱"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 괄호 추출 시도
        for bracket in ["{", "["]:
            start = response.find(bracket)
            if start >= 0:
                try:
                    return json.loads(response[start:])
                except json.JSONDecodeError:
                    continue
        
        # 최후의 수단
        return {"objects": []}
    
    def _parse_llm_response(self, data: Dict[str, Any], image_size: tuple, 
                           offset_bbox: Optional[BoundingBox] = None) -> List[DetectionResult]:
        """LLM 응답 파싱"""
        detections = []
        
        objects = data.get("objects", [])
        if not isinstance(objects, list):
            return detections
        
        image_width, image_height = image_size
        
        for obj in objects:
            try:
                # 기본 정보 추출
                name = str(obj.get("name", "")).strip()
                bbox_data = obj.get("bbox", [0, 0, 0, 0])
                confidence = float(obj.get("confidence", 0.0))
                
                # 신뢰도 임계값 체크
                conf_threshold = self.runtime_config.get("conf_threshold", 0.5)
                if confidence < conf_threshold:
                    continue
                
                # 바운딩 박스 처리
                if offset_bbox:
                    # 패치 분석 결과 - 좌표 조정
                    x = bbox_data[0] + offset_bbox.x
                    y = bbox_data[1] + offset_bbox.y
                    w = bbox_data[2]
                    h = bbox_data[3]
                else:
                    # 전체 이미지 분석 결과
                    x, y, w, h = bbox_data
                
                # 좌표 정규화
                x = max(0, min(int(x), image_width))
                y = max(0, min(int(y), image_height))
                w = max(1, min(int(w), image_width - x))
                h = max(1, min(int(h), image_height - y))
                
                bbox = BoundingBox(x, y, w, h)
                
                # 택소노미 정규화
                if self.taxonomy:
                    taxonomy_result = self.taxonomy.normalize(name)
                    canonical_name = taxonomy_result.canonical_name
                    taxonomy_confidence = taxonomy_result.confidence
                    
                    # 최종 신뢰도 계산
                    final_confidence = min(confidence, taxonomy_confidence)
                else:
                    canonical_name = name
                    final_confidence = confidence
                
                # 감지 결과 생성
                detection = DetectionResult(
                    bbox=bbox,
                    label=canonical_name,
                    confidence=round(final_confidence, 4),
                    cloud_provider=self.cloud_provider,
                    status=DetectionStatus.DETECTED
                )
                
                detections.append(detection)
                
            except Exception as e:
                print(f"⚠️ 객체 파싱 실패: {e}")
                continue
        
        return detections
    
    def get_llm_statistics(self) -> Dict[str, Any]:
        """
        LLM 특화 통계 정보
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        return {
            **self.get_statistics(),
            "llm_method": "large_language_model",
            "llm_config": self.llm_config,
            "prompt_config": self.prompt_config,
            "runtime_config": self.runtime_config
        }
