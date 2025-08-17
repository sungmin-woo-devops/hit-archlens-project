"""
AWS LLM 기반 다이어그램 오토라벨러
LLM Vision API를 사용하여 AWS 다이어그램에서 서비스 아이콘을 인식하고 바운딩 박스를 생성합니다.
"""

import os
import json
import yaml
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import numpy as np
from tqdm import tqdm

from llm_providers import LLMProvider, OpenAIProvider, DeepSeekProvider
from prompts import PromptManager
from utils.io_utils import load_image, save_json, list_images
from utils.proposals import propose_regions
from utils.taxonomy import Taxonomy
from utils.exporters import to_labelstudio, to_yolo, to_coco

@dataclass
class DetectionResult:
    """감지 결과 데이터 클래스"""
    bbox: List[int]  # [x, y, w, h]
    label: str
    confidence: float
    service_code: str = ""

@dataclass
class AnalysisResult:
    """분석 결과 데이터 클래스"""
    image_path: str
    width: int
    height: int
    detections: List[DetectionResult]
    processing_time: float

class AWSLLMAutoLabeler:
    """
    AWS LLM 기반 다이어그램 오토라벨러
    
    LLM Vision API를 사용하여 AWS 다이어그램에서 서비스 아이콘을 인식하고
    바운딩 박스를 생성합니다.
    
    사용 예시:
    ```python
    labeler = AWSLLMAutoLabeler("config.yaml")
    results = labeler.analyze_image("diagram.png")
    labeler.export_results(results, "output/", "json")
    ```
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        LLM 오토라벨러 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.taxonomy = self._load_taxonomy()
        self.llm_provider = self._setup_llm_provider()
        self.prompt_manager = PromptManager()
        
        print(f"✅ LLM 오토라벨러 초기화 완료")
        print(f"   - 제공자: {self.config['provider']}")
        print(f"   - 모드: {self.config['mode']}")
        print(f"   - 신뢰도 임계값: {self.config['runtime']['conf_threshold']}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """설정 파일 로드"""
        config_file = Path(config_path)
        if not config_file.is_absolute():
            config_file = Path(__file__).parent.parent / config_path
        
        with open(config_file, "r", encoding="utf-8") as f:
            raw = f.read()
        
        # 환경변수 확장
        raw = os.path.expandvars(raw)
        return yaml.safe_load(raw)
    
    def _load_taxonomy(self) -> Taxonomy:
        """택소노미 로드"""
        taxonomy_path = Path(self.config["data"]["taxonomy_csv"])
        if not taxonomy_path.is_absolute():
            taxonomy_path = Path(__file__).parent.parent / taxonomy_path
        
        return Taxonomy.from_csv(str(taxonomy_path))
    
    def _setup_llm_provider(self) -> LLMProvider:
        """LLM 제공자 설정"""
        provider_name = self.config["provider"]
        
        if provider_name == "openai":
            return OpenAIProvider(
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                api_key=os.getenv("OPENAI_API_KEY"),
                vision_model=self.config["openai"]["vision_model"]
            )
        elif provider_name == "deepseek":
            return DeepSeekProvider(
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                vision_model=self.config["deepseek"]["vision_model"]
            )
        else:
            raise ValueError(f"지원하지 않는 제공자: {provider_name}")
    
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
    
    def _normalize_detection(self, detection: Dict[str, Any], 
                           image_width: int, image_height: int) -> Optional[DetectionResult]:
        """감지 결과 정규화"""
        name = str(detection.get("name", "")).strip()
        bbox = detection.get("bbox", [0, 0, 0, 0])
        confidence = float(detection.get("confidence", 0.0))
        
        # 신뢰도 임계값 체크
        if confidence < float(self.config["runtime"]["conf_threshold"]):
            return None
        
        # 택소노미 정규화
        canonical_name, taxonomy_score = self.taxonomy.normalize(name)
        
        # 바운딩 박스 정규화
        x, y, w, h = bbox
        x = max(0, min(int(x), image_width))
        y = max(0, min(int(y), image_height))
        w = max(1, min(int(w), image_width - x))
        h = max(1, min(int(h), image_height - y))
        
        # 최종 신뢰도 계산
        final_confidence = min(confidence, taxonomy_score)
        
        return DetectionResult(
            bbox=[x, y, w, h],
            label=canonical_name,
            confidence=round(final_confidence, 4),
            service_code=canonical_name
        )
    
    def analyze_image(self, image_path: str) -> AnalysisResult:
        """
        단일 이미지 분석
        
        Args:
            image_path: 분석할 이미지 경로
            
        Returns:
            AnalysisResult: 분석 결과
        """
        start_time = time.time()
        
        # 이미지 로드
        image = load_image(image_path)
        width, height = image.size
        
        # 모드에 따른 분석
        if self.config["mode"] == "full_image_llm":
            detections = self._analyze_full_image(image)
        else:  # patch_llm
            detections = self._analyze_patch_llm(image)
        
        processing_time = time.time() - start_time
        
        return AnalysisResult(
            image_path=image_path,
            width=width,
            height=height,
            detections=detections,
            processing_time=processing_time
        )
    
    def _analyze_full_image(self, image: Image.Image) -> List[DetectionResult]:
        """전체 이미지 LLM 분석"""
        prompt = self.prompt_manager.get_full_image_prompt()
        response = self.llm_provider.analyze_image(image, prompt)
        data = self._safe_json_parse(response)
        
        detections = []
        for obj in data.get("objects", []):
            detection = self._normalize_detection(obj, image.width, image.height)
            if detection:
                detections.append(detection)
        
        return detections
    
    def _analyze_patch_llm(self, image: Image.Image) -> List[DetectionResult]:
        """패치별 LLM 분석"""
        import cv2
        
        # 이미지를 OpenCV 형식으로 변환
        img_array = np.array(image)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # 객체 제안
        boxes = propose_regions(img_bgr)
        
        detections = []
        prompt = self.prompt_manager.get_patch_prompt()
        
        for x, y, w, h in boxes:
            # 이미지 크롭
            crop = image.crop((x, y, x + w, y + h))
            
            # LLM 분석
            response = self.llm_provider.analyze_image(crop, prompt)
            data = self._safe_json_parse(response)
            
            # 후보들 중 최고 점수 선택
            candidates = data.get("candidates", [])
            best_label, best_score = None, 0.0
            
            for candidate in candidates:
                canonical_name, score = self.taxonomy.normalize(str(candidate))
                if score > best_score:
                    best_label, best_score = canonical_name, score
            
            # 임계값 체크
            if best_label and best_score >= 0.5:
                detection = DetectionResult(
                    bbox=[x, y, w, h],
                    label=best_label,
                    confidence=round(best_score, 3),
                    service_code=best_label
                )
                detections.append(detection)
        
        return detections
    
    def analyze_batch(self, image_paths: List[str]) -> List[AnalysisResult]:
        """
        배치 이미지 분석
        
        Args:
            image_paths: 분석할 이미지 경로 리스트
            
        Returns:
            List[AnalysisResult]: 분석 결과 리스트
        """
        results = []
        
        for image_path in tqdm(image_paths, desc="LLM 분석"):
            try:
                result = self.analyze_image(image_path)
                results.append(result)
            except Exception as e:
                print(f"⚠️ 이미지 분석 실패: {image_path} - {e}")
                continue
        
        return results
    
    def export_results(self, results: List[AnalysisResult], 
                      output_dir: str, format: str = "json") -> str:
        """
        결과 내보내기
        
        Args:
            results: 분석 결과 리스트
            output_dir: 출력 디렉터리
            format: 출력 형식 (json, yolo, coco, labelstudio)
            
        Returns:
            str: 출력 파일 경로
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 결과를 내보내기 형식으로 변환
        items = []
        for result in results:
            objects = []
            for detection in result.detections:
                objects.append({
                    "bbox": detection.bbox,
                    "label": detection.label,
                    "score": detection.confidence
                })
            
            items.append({
                "image_path": result.image_path,
                "width": result.width,
                "height": result.height,
                "objects": objects
            })
        
        # 형식별 내보내기
        if format == "yolo":
            output_path = os.path.join(output_dir, "yolo")
            to_yolo(items, output_path)
        elif format == "coco":
            output_path = os.path.join(output_dir, "coco.json")
            save_json(output_path, to_coco(items))
        elif format == "labelstudio":
            output_path = os.path.join(output_dir, "labelstudio.json")
            save_json(output_path, to_labelstudio(items))
        else:  # json
            output_path = os.path.join(output_dir, "results.json")
            save_json(output_path, items)
        
        print(f"✅ 결과 내보내기 완료: {output_path}")
        return output_path
    
    def get_statistics(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        """분석 결과 통계"""
        stats = {
            "total_images": len(results),
            "total_detections": sum(len(r.detections) for r in results),
            "avg_detections_per_image": 0,
            "avg_processing_time": 0,
            "service_distribution": {},
            "confidence_distribution": {
                "high": 0,    # >= 0.8
                "medium": 0,  # 0.5-0.8
                "low": 0      # < 0.5
            }
        }
        
        if results:
            stats["avg_detections_per_image"] = stats["total_detections"] / len(results)
            stats["avg_processing_time"] = sum(r.processing_time for r in results) / len(results)
        
        # 서비스별 분포
        for result in results:
            for detection in result.detections:
                service = detection.label
                stats["service_distribution"][service] = stats["service_distribution"].get(service, 0) + 1
                
                # 신뢰도 분포
                if detection.confidence >= 0.8:
                    stats["confidence_distribution"]["high"] += 1
                elif detection.confidence >= 0.5:
                    stats["confidence_distribution"]["medium"] += 1
                else:
                    stats["confidence_distribution"]["low"] += 1
        
        return stats
