"""
AWS 다이어그램 오토라벨링 모듈
AWS 아키텍처 다이어그램에서 AWS 서비스 아이콘을 자동으로 인식하고 바운딩 박스를 생성합니다.

주요 기능:
- CLIP 기반 아이콘 유사도 검색
- ORB 특징점 매칭으로 정밀도 향상
- OCR 텍스트 힌트 활용
- NMS로 중복 제거
- 다양한 출력 형식 지원 (YOLO, Label Studio, JSON)
"""

import os
import cv2
import torch
import numpy as np
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from PIL import Image
from tqdm import tqdm
import faiss
import open_clip

# 내부 모듈 임포트
from .icon_scanner import IconScanner, IconInfo
from .image_utils import safe_load_image, process_icon_for_clip
from .proposals import propose
from .taxonomy import Taxonomy
from .orb_refine import orb_score
from .ocr_hint import ocr_text
from .exporters import to_labelstudio, to_yolo

@dataclass
class DetectionResult:
    """탐지 결과 데이터 클래스"""
    bbox: List[int]  # [x, y, width, height]
    label: str       # AWS 서비스명
    confidence: float # 신뢰도 점수 (0.0-1.0)
    service_code: str # AWS 서비스 코드

@dataclass
class AnalysisResult:
    """분석 결과 데이터 클래스"""
    image_path: str
    width: int
    height: int
    detections: List[DetectionResult]
    processing_time: float

class AWSDiagramAutoLabeler:
    """
    AWS 다이어그램 오토라벨링 클래스
    
    사용 예시:
    ```python
    # 초기화
    labeler = AWSDiagramAutoLabeler(
        icons_dir="path/to/aws/icons",
        taxonomy_csv="path/to/taxonomy.csv",
        config={
            "clip_name": "ViT-B-32",
            "clip_pretrained": "openai",
            "detect": {
                "max_size": 1600,
                "canny_low": 60,
                "canny_high": 160,
                "mser_delta": 5,
                "min_area": 900,
                "max_area": 90000,
                "win": 128,
                "stride": 96,
                "iou_nms": 0.45
            },
            "retrieval": {
                "topk": 5,
                "orb_nfeatures": 500,
                "score_clip_w": 0.6,
                "score_orb_w": 0.3,
                "score_ocr_w": 0.1,
                "accept_score": 0.5
            },
            "ocr": {
                "enabled": True,
                "lang": ["en"]
            }
        }
    )
    
    # 단일 이미지 분석
    result = labeler.analyze_image("path/to/diagram.png")
    
    # 배치 분석
    results = labeler.analyze_batch(["diagram1.png", "diagram2.png"])
    
    # 결과 내보내기
    labeler.export_results(results, "output_dir", format="yolo")
    ```
    """
    
    def __init__(self, icons_dir: str, taxonomy_csv: str, config: Dict):
        """
        AWS 다이어그램 오토라벨러 초기화
        
        Args:
            icons_dir: AWS 아이콘 디렉터리 경로
            taxonomy_csv: AWS 서비스 택소노미 CSV 파일 경로
            config: 설정 딕셔너리
        """
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 택소노미 로드
        # 개선된 택소노미 로드 (규칙 파일 포함)
        rules_dir = os.path.join(os.path.dirname(taxonomy_csv), "rules")
        self.taxonomy = Taxonomy.from_csv(taxonomy_csv, rules_dir)
        
        # 아이콘 스캐너 초기화
        self.icon_scanner = IconScanner(icons_dir, taxonomy_csv)
        
        # CLIP 모델 로드
        self.model, self.preprocess = self._load_clip_model()
        
        # 아이콘 인덱스 빌드
        self.icons, self.icon_features, self.icon_index = self._build_icon_index()
        
        print(f"✅ AWS 다이어그램 오토라벨러 초기화 완료")
        print(f"   - 장치: {self.device}")
        print(f"   - 로드된 아이콘: {len(self.icons)}개")
        print(f"   - 택소노미 서비스: {len(self.taxonomy.names)}개")
    
    def _load_clip_model(self) -> Tuple[torch.nn.Module, callable]:
        """CLIP 모델 로드"""
        model, preprocess, _ = open_clip.create_model_and_transforms(
            self.config["clip_name"],
            pretrained=self.config["clip_pretrained"],
            device=self.device
        )
        model.eval()
        return model, preprocess
    
    def _build_icon_index(self) -> Tuple[List[IconInfo], np.ndarray, faiss.Index]:
        """아이콘 인덱스 빌드"""
        print("🔍 AWS 아이콘 인덱스 빌드 중...")
        
        # 아이콘 스캔
        icons = self.icon_scanner.scan_icons()
        if not icons:
            raise ValueError("스캔된 AWS 아이콘이 없습니다!")
        
        # 임베딩 생성
        features = []
        valid_icons = []
        
        for icon in tqdm(icons, desc="아이콘 임베딩 생성"):
            try:
                # 이미지 로드 및 전처리
                icon_path = Path(self.icon_scanner.icons_dir) / icon.file_path
                if not icon_path.exists():
                    continue
                
                pil = safe_load_image(str(icon_path))
                if not pil:
                    continue
                
                # CLIP 전처리
                pil_processed = process_icon_for_clip(pil)
                
                # 임베딩 생성
                feat = self._img_to_feat(pil_processed)
                if feat is not None:
                    features.append(feat)
                    valid_icons.append(icon)
                
            except Exception as e:
                print(f"⚠️ 아이콘 처리 실패: {icon.file_path} - {e}")
                continue
        
        if not features:
            raise ValueError("처리된 아이콘이 없습니다!")
        
        # FAISS 인덱스 생성
        features = np.stack(features).astype("float32")
        index = faiss.IndexFlatIP(features.shape[1])
        index.add(features)
        
        print(f"✅ 인덱스 생성 완료: {len(valid_icons)}개 아이콘")
        return valid_icons, features, index
    
    def _img_to_feat(self, pil: Image.Image) -> Optional[np.ndarray]:
        """이미지를 CLIP 임베딩으로 변환"""
        try:
            with torch.no_grad():
                im = self.preprocess(pil).unsqueeze(0).to(self.device)
                f = self.model.encode_image(im)
                f = f / f.norm(dim=-1, keepdim=True)
            return f.squeeze(0).cpu().numpy()
        except Exception as e:
            print(f"⚠️ 임베딩 생성 실패: {e}")
            return None
    
    def _search_similar_icons(self, query_feat: np.ndarray, topk: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """유사한 아이콘 검색"""
        D, I = self.icon_index.search(query_feat.reshape(1, -1), topk)
        return D[0], I[0]
    
    def _calculate_scores(self, crop: Image.Image, icon_ref: np.ndarray) -> Tuple[float, float, float]:
        """CLIP, ORB, OCR 점수 계산"""
        # CLIP 점수
        query_feat = self._img_to_feat(crop)
        if query_feat is None:
            return 0.0, 0.0, 0.0
        
        D, I = self._search_similar_icons(query_feat, 1)
        if len(I) == 0:
            return 0.0, 0.0, 0.0
        
        clip_score = float((D[0] + 1) / 2)
        
        # ORB 점수
        crop_bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
        orb_score_val = orb_score(
            crop_bgr, 
            icon_ref, 
            nfeatures=self.config["retrieval"]["orb_nfeatures"]
        )
        
        # OCR 점수
        ocr_score = 0.0
        if self.config["ocr"]["enabled"]:
            txt = ocr_text(crop, tuple(self.config["ocr"]["lang"]))
            ocr_score = 0.2 if (txt and len(txt) <= 12) else 0.0
        
        return clip_score, orb_score_val, ocr_score
    
    def _nms(self, detections: List[DetectionResult], iou_threshold: float = 0.45) -> List[DetectionResult]:
        """Non-Maximum Suppression으로 중복 제거"""
        if not detections:
            return []
        
        boxes = np.array([d.bbox for d in detections])
        scores = np.array([d.confidence for d in detections])
        
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 0] + boxes[:, 2]
        y2 = boxes[:, 1] + boxes[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        
        order = scores.argsort()[::-1]
        keep = []
        
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]
        
        return [detections[i] for i in keep]
    
    def analyze_image(self, image_path: str) -> AnalysisResult:
        """
        단일 이미지 분석
        
        Args:
            image_path: 분석할 이미지 경로
            
        Returns:
            AnalysisResult: 분석 결과
        """
        import time
        start_time = time.time()
        
        # 이미지 로드
        img_bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError(f"이미지를 로드할 수 없습니다: {image_path}")
        
        H, W = img_bgr.shape[:2]
        
        # 객체 제안
        boxes = propose(img_bgr, self.config["detect"])
        
        detections = []
        
        for (x, y, w, h) in boxes:
            # 경계 확인
            x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
            if x1 - x0 < 24 or y1 - y0 < 24:
                continue
            
            # 이미지 크롭
            crop = Image.fromarray(cv2.cvtColor(img_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))
            
            # 유사한 아이콘 검색
            query_feat = self._img_to_feat(crop)
            if query_feat is None:
                continue
            
            D, I = self._search_similar_icons(query_feat, self.config["retrieval"]["topk"])
            if len(I) == 0:
                continue
            
            # 최적 매칭 아이콘 선택
            best_i = int(I[0])
            if best_i >= len(self.icons):
                continue
            
            icon_info = self.icons[best_i]
            icon_ref = cv2.cvtColor(
                np.array(process_icon_for_clip(
                    safe_load_image(str(Path(self.icon_scanner.icons_dir) / icon_info.file_path))
                )), 
                cv2.COLOR_RGB2BGR
            )
            
            # 점수 계산
            clip_s, orb_s, ocr_s = self._calculate_scores(crop, icon_ref)
            
            # 가중합 점수
            final_score = (
                self.config["retrieval"]["score_clip_w"] * clip_s +
                self.config["retrieval"]["score_orb_w"] * orb_s +
                self.config["retrieval"]["score_ocr_w"] * ocr_s
            )
            
            # 임계값 필터링
            if final_score < self.config["retrieval"]["accept_score"]:
                continue
            
            # 라벨 정규화
            label, nsc = self.taxonomy.normalize(icon_info.service_name)
            confidence = round(final_score * 0.7 + nsc * 0.3, 4)
            
            detections.append(DetectionResult(
                bbox=[x0, y0, x1 - x0, y1 - y0],
                label=label,
                confidence=confidence,
                service_code=icon_info.service_code
            ))
        
        # NMS 적용
        if detections:
            detections = self._nms(detections, self.config["detect"]["iou_nms"])
            detections = sorted(detections, key=lambda d: -d.confidence)
        
        processing_time = time.time() - start_time
        
        return AnalysisResult(
            image_path=image_path,
            width=W,
            height=H,
            detections=detections,
            processing_time=processing_time
        )
    
    def analyze_batch(self, image_paths: List[str]) -> List[AnalysisResult]:
        """
        배치 이미지 분석
        
        Args:
            image_paths: 분석할 이미지 경로 리스트
            
        Returns:
            List[AnalysisResult]: 분석 결과 리스트
        """
        results = []
        for image_path in tqdm(image_paths, desc="배치 분석"):
            try:
                result = self.analyze_image(image_path)
                results.append(result)
            except Exception as e:
                print(f"⚠️ 이미지 분석 실패: {image_path} - {e}")
                continue
        return results
    
    def export_results(self, results: List[AnalysisResult], output_dir: str, 
                      format: str = "json") -> str:
        """
        분석 결과 내보내기
        
        Args:
            results: 분석 결과 리스트
            output_dir: 출력 디렉터리
            format: 출력 형식 ("json", "yolo", "labelstudio")
            
        Returns:
            str: 출력 파일 경로
        """
        os.makedirs(output_dir, exist_ok=True)
        
        if format == "json":
            # JSON 형식으로 내보내기
            output_data = []
            for result in results:
                output_data.append({
                    "image_path": result.image_path,
                    "width": result.width,
                    "height": result.height,
                    "processing_time": result.processing_time,
                    "detections": [
                        {
                            "bbox": d.bbox,
                            "label": d.label,
                            "confidence": d.confidence,
                            "service_code": d.service_code
                        }
                        for d in result.detections
                    ]
                })
            
            output_path = os.path.join(output_dir, "detections.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            return output_path
        
        elif format == "yolo":
            # YOLO 형식으로 내보내기
            yolo_data = []
            for result in results:
                yolo_data.append({
                    "image_path": result.image_path,
                    "width": result.width,
                    "height": result.height,
                    "objects": [
                        {
                            "bbox": d.bbox,
                            "label": d.label,
                            "score": d.confidence
                        }
                        for d in result.detections
                    ]
                })
            
            yolo_dir = os.path.join(output_dir, "yolo")
            to_yolo(yolo_data, yolo_dir)
            return yolo_dir
        
        elif format == "labelstudio":
            # Label Studio 형식으로 내보내기
            ls_data = []
            for result in results:
                ls_data.append({
                    "image_path": result.image_path,
                    "width": result.width,
                    "height": result.height,
                    "objects": [
                        {
                            "bbox": d.bbox,
                            "label": d.label,
                            "score": d.confidence
                        }
                        for d in result.detections
                    ]
                })
            
            ls_json = to_labelstudio(ls_data)
            output_path = os.path.join(output_dir, "labelstudio.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(ls_json, f, ensure_ascii=False, indent=2)
            
            return output_path
        
        else:
            raise ValueError(f"지원하지 않는 형식: {format}")
    
    def get_statistics(self, results: List[AnalysisResult]) -> Dict:
        """분석 결과 통계"""
        total_images = len(results)
        total_detections = sum(len(r.detections) for r in results)
        avg_processing_time = np.mean([r.processing_time for r in results])
        
        # 서비스별 통계
        service_counts = {}
        for result in results:
            for detection in result.detections:
                service_counts[detection.label] = service_counts.get(detection.label, 0) + 1
        
        return {
            "total_images": total_images,
            "total_detections": total_detections,
            "avg_processing_time": avg_processing_time,
            "detection_rate": total_detections / total_images if total_images > 0 else 0,
            "service_distribution": service_counts
        }
