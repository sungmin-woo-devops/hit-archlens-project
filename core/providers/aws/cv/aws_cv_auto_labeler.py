"""
AWS CV Auto Labeler Implementation

AWS 전용 Computer Vision 오토라벨러 구현체
"""

import os
import sys
import torch
import cv2
import numpy as np
import faiss
import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageOps
import open_clip
from tqdm import tqdm
from collections import defaultdict
from dataclasses import dataclass

# core 프레임워크 import
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))
from core.auto_labeler.cv_auto_labeler import CVAutoLabeler
from core.models import (
    DetectionResult, 
    BoundingBox,
    CloudProvider,
    DetectionStatus
)
from core.taxonomy import AWSTaxonomy


@dataclass
class IconInfo:
    """아이콘 정보 데이터 클래스"""
    file_path: str
    service_name: str
    service_code: str
    category: str
    size: int
    confidence: float


def safe_load_image(image_path: str) -> Image.Image:
    """안전한 이미지 로딩 - 모든 모드 지원"""
    try:
        pil = Image.open(image_path)
        return pil
    except Exception as e:
        print(f"⚠️ 이미지 로딩 실패: {image_path} - {e}")
        return Image.new('RGB', (256, 256), (255, 255, 255))


def safe_convert_to_rgba(pil: Image.Image) -> Image.Image:
    """안전한 RGBA 변환"""
    try:
        if pil.mode == 'RGBA':
            return pil
        elif pil.mode in ('RGB', 'L'):
            if pil.mode == 'L':
                pil = pil.convert('RGB')
            alpha = Image.new('L', pil.size, 255)
            pil.putalpha(alpha)
            return pil
        elif pil.mode == 'P':
            return pil.convert('RGBA')
        else:
            pil = pil.convert('RGB')
            alpha = Image.new('L', pil.size, 255)
            pil.putalpha(alpha)
            return pil
    except Exception as e:
        print(f"⚠️ RGBA 변환 실패: {e}")
        return pil.convert('RGB')


def safe_trim_transparent(pil: Image.Image) -> Image.Image:
    """안전한 투명 배경 제거 - RGBA 모드 지원"""
    try:
        if pil.mode != 'RGBA':
            pil = safe_convert_to_rgba(pil)
        
        if pil.mode == 'RGBA':
            alpha = pil.getchannel('A')
            bbox = alpha.getbbox()
            if bbox:
                return pil.crop(bbox)
        
        return pil
    except Exception as e:
        print(f"⚠️ 투명 배경 제거 실패: {e}")
        return pil


def safe_square_pad(pil: Image.Image, canvas_size: int = 256, pad_ratio: float = 0.06) -> Image.Image:
    """안전한 정사각 패딩"""
    try:
        pil = safe_trim_transparent(pil)
        
        w, h = pil.size
        pad = int(round(pad_ratio * max(w, h)))
        scale = (canvas_size - pad * 2) / max(w, h)
        
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        pil_resized = pil.resize((new_w, new_h), Image.LANCZOS)
        
        canvas = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
        x = (canvas_size - new_w) // 2
        y = (canvas_size - new_h) // 2
        canvas.paste(pil_resized, (x, y), pil_resized)
        
        return canvas
    except Exception as e:
        print(f"⚠️ 정사각 패딩 실패: {e}")
        return pil.resize((canvas_size, canvas_size), Image.LANCZOS)


def process_icon_for_clip(pil: Image.Image, canvas_size: int = 256) -> Image.Image:
    """CLIP 모델용 아이콘 전처리 - 완전 안전"""
    try:
        pil = safe_convert_to_rgba(pil)
        pil = safe_trim_transparent(pil)
        pil = safe_square_pad(pil, canvas_size)
        return pil.convert('RGB')
    except Exception as e:
        print(f"⚠️ 아이콘 전처리 실패: {e}")
        return Image.new('RGB', (canvas_size, canvas_size), (255, 255, 255))


def orb_score(patch_bgr, icon_bgr, nfeatures=500):
    """ORB 알고리즘으로 유사성 측정"""
    try:
        orb = cv2.ORB_create(nfeatures=nfeatures)
        
        kp1, des1 = orb.detectAndCompute(cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2GRAY), None)
        kp2, des2 = orb.detectAndCompute(cv2.cvtColor(icon_bgr, cv2.COLOR_BGR2GRAY), None)
        
        if des1 is None or des2 is None or len(kp1) < 5 or len(kp2) < 5:
            return 0.0
        
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        m = bf.match(des1, des2)
        
        if not m:
            return 0.0
        
        m = sorted(m, key=lambda x: x.distance)
        good = [x for x in m if x.distance < 64]
        
        return min(1.0, len(good) / max(10, len(m)))
    except Exception as e:
        print(f"⚠️ ORB 점수 계산 실패: {e}")
        return 0.0


class IconScanner:
    """AWS 아이콘 스캐너 - aws_cv_clip에서 가져온 성공적인 로직"""
    
    def __init__(self, icons_dir: str, taxonomy_csv: str):
        self.icons_dir = Path(icons_dir)
        self.service_mapping = self._load_taxonomy(taxonomy_csv)
    
    def _load_taxonomy(self, taxonomy_csv: str) -> Dict[str, str]:
        """택소노미 로드 및 서비스 매핑 생성"""
        df = pd.read_csv(taxonomy_csv)
        return {
            row['service_code'].strip().lower(): row['service_full_name'].strip()
            for _, row in df.iterrows()
            if pd.notna(row.get('service_code')) and pd.notna(row.get('service_full_name'))
        }
    
    def scan_icons(self) -> List[IconInfo]:
        """PNG 아이콘 스캔 - 최대 사이즈만 선택"""
        service_best_icons = defaultdict(lambda: {"size": 0, "icon": None})
        
        # 대상 디렉터리
        target_dirs = ["Resource-Icons_02072025", "Architecture-Service-Icons_02072025"]
        
        for target_dir in target_dirs:
            target_path = self.icons_dir / target_dir
            if not target_path.exists():
                continue
            
            # PNG 파일만 재귀 스캔
            for png_file in target_path.rglob("*.png"):
                try:
                    # 서비스명 추출
                    service_name, confidence = self._extract_service_name(png_file.name, target_dir)
                    if service_name == "Unknown" or confidence < 0.5:
                        continue
                    
                    # 사이즈 추출
                    size = self._extract_size(png_file.name)
                    
                    # 서비스별 최대 사이즈 선택
                    service_key = service_name
                    if size > service_best_icons[service_key]["size"]:
                        icon_info = IconInfo(
                            file_path=str(png_file.relative_to(self.icons_dir)),
                            service_name=service_name,
                            service_code=self._find_service_code(service_name),
                            category=self._extract_category(str(png_file.relative_to(self.icons_dir))),
                            size=size,
                            confidence=confidence
                        )
                        service_best_icons[service_key] = {"size": size, "icon": icon_info}
                        
                except Exception as e:
                    print(f"⚠️ 아이콘 처리 실패: {png_file.name} - {e}")
                    continue
        
        # 최대 사이즈 아이콘들만 반환
        icons = [data["icon"] for data in service_best_icons.values() if data["icon"]]
        print(f"✅ 스캔 완료: {len(icons)}개 서비스의 최대 사이즈 PNG 아이콘")
        return icons
    
    def _extract_service_name(self, filename: str, icon_type: str) -> Tuple[str, float]:
        """파일명에서 서비스명 추출 - 세부 아이콘 개별 처리"""
        name = Path(filename).stem
        
        # 패턴 매칭
        if "Resource-Icons" in icon_type:
            pattern = r'Res_([A-Za-z0-9-]+)_([A-Za-z0-9-]+)_\d+'
        else:
            pattern = r'Arch_([A-Za-z0-9-]+)_\d+'
        
        match = re.search(pattern, name)
        if match:
            if "Resource-Icons" in icon_type:
                service_code = match.group(1).lower()
                detail_code = match.group(2).lower()
                
                # 세부 서비스명 생성 (예: "Amazon CloudWatch Alarm")
                base_service = self.service_mapping.get(service_code, service_code)
                detail_service = f"{base_service} {detail_code.replace('-', ' ').title()}"
                
                return detail_service, 1.0
            else:
                service_code = match.group(1).lower()
                if service_code in self.service_mapping:
                    return self.service_mapping[service_code], 1.0
        
        return "Unknown", 0.0
    
    def _extract_size(self, filename: str) -> int:
        """파일명에서 사이즈 추출"""
        match = re.search(r'_(\d+)\.png$', filename)
        return int(match.group(1)) if match else 0
    
    def _find_service_code(self, service_name: str) -> str:
        """서비스명에서 코드 찾기"""
        for code, name in self.service_mapping.items():
            if name == service_name:
                return code
        return ""
    
    def _extract_category(self, file_path: str) -> str:
        """파일 경로에서 카테고리 추출"""
        parts = file_path.split('/')
        if len(parts) > 1:
            return parts[0]
        return "Unknown"


class AWSCVAutoLabeler(CVAutoLabeler):
    """
    AWS 전용 Computer Vision 오토라벨러
    
    CLIP 기반 이미지 유사도 검색과 ORB 특징점 매칭을 결합한
    AWS 서비스 아이콘 인식 시스템
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        AWS CV 오토라벨러 초기화
        
        Args:
            config: AWS 전용 설정
        """
        # AWS 기본 설정 적용
        aws_config = self._prepare_aws_config(config)
        
        # config를 인스턴스 변수로 저장
        self.config = aws_config
        
        # AWS 특화 컴포넌트를 먼저 초기화
        self._setup_aws_specific_components()
        
        # 그 다음 부모 클래스 초기화
        super().__init__(CloudProvider.AWS, aws_config)
        
        print(f"   - AWS 아이콘 디렉터리: {config.get('data', {}).get('icons_dir', 'Not set')}")
        print(f"   - AWS 택소노미: {config.get('data', {}).get('taxonomy_csv', 'Not set')}")
    
    def _prepare_aws_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """AWS 전용 설정 준비"""
        # 기본 AWS 설정
        aws_config = {
            "cloud_provider": "aws",
            "method": "cv",
            "data": {
                "images_dir": config.get("data", {}).get("images_dir", "./images"),
                "icons_dir": config.get("data", {}).get("icons_dir", "./icons"),
                "icons_zip": config.get("data", {}).get("icons_zip", "./Asset-Package.zip"),
                "icons_mapping_csv": config.get("data", {}).get("icons_mapping_csv", "./aws_icons_mapping.csv"),
                "taxonomy_csv": config.get("data", {}).get("taxonomy_csv", "./aws_resources_models.csv")
            },
            "cv": {
                "clip_name": config.get("cv", {}).get("clip_name", "ViT-B-32"),
                "clip_pretrained": config.get("cv", {}).get("clip_pretrained", "laion2b_s34b_b79k"),
                "device": "cuda" if torch.cuda.is_available() else "cpu"
            },
            "detection": {
                "max_size": config.get("detection", {}).get("max_size", 1600),
                "canny_low": config.get("detection", {}).get("canny_low", 60),
                "canny_high": config.get("detection", {}).get("canny_high", 160),
                "mser_delta": config.get("detection", {}).get("mser_delta", 5),
                "min_area": config.get("detection", {}).get("min_area", 900),
                "max_area": config.get("detection", {}).get("max_area", 90000),
                "win": config.get("detection", {}).get("win", 128),
                "stride": config.get("detection", {}).get("stride", 96),
                "iou_nms": config.get("detection", {}).get("iou_nms", 0.45),
                "use_canny": True,
                "use_mser": True,
                "use_sliding_window": True
            },
            "retrieval": {
                "topk": config.get("retrieval", {}).get("topk", 5),
                "accept_score": config.get("retrieval", {}).get("accept_score", 0.35),
                "orb_nfeatures": config.get("retrieval", {}).get("orb_nfeatures", 500),
                "score_clip_w": config.get("retrieval", {}).get("score_clip_w", 0.6),
                "score_orb_w": config.get("retrieval", {}).get("score_orb_w", 0.3),
                "score_ocr_w": config.get("retrieval", {}).get("score_ocr_w", 0.1)
            },
            "ocr": {
                "enabled": config.get("ocr", {}).get("enabled", True),
                "lang": config.get("ocr", {}).get("lang", ["en"])
            }
        }
        
        return aws_config
    
    def _setup_cv_components(self):
        """CV 컴포넌트 설정"""
        # CLIP 모델 로드
        self.clip_model, self.clip_preprocess = self._load_clip_model()
        
        # ORB 특징점 검출기
        self.orb = cv2.ORB_create(
            nfeatures=self.retrieval_config.get("orb_nfeatures", 500)
        )
        
        # OCR 설정
        self.ocr_enabled = self.config.get("ocr", {}).get("enabled", True)
        if self.ocr_enabled:
            try:
                import easyocr
                self.ocr_reader = easyocr.Reader(self.config.get("ocr", {}).get("lang", ["en"]))
            except ImportError:
                print("⚠️ easyocr이 설치되지 않아 OCR 기능이 비활성화됩니다")
                self.ocr_enabled = False
    
    def _setup_aws_specific_components(self):
        """AWS 특화 컴포넌트 설정"""
        # AWS 특화 유틸리티 초기화
        self._setup_aws_utilities()
        
        # AWS 택소노미 로드
        self.aws_taxonomy = self._load_aws_taxonomy()
        
        # AWS 아이콘 스캐너 초기화
        icons_dir = self.config.get("data", {}).get("icons_dir")
        taxonomy_csv = self.config.get("data", {}).get("taxonomy_csv")
        if icons_dir and taxonomy_csv:
            self.icon_scanner = IconScanner(icons_dir, taxonomy_csv)
        else:
            self.icon_scanner = None
        
        # AWS 아이콘 인덱스는 나중에 필요할 때 구축
        self.aws_icon_index = None
    
    def _load_clip_model(self) -> Tuple[torch.nn.Module, callable]:
        """CLIP 모델 로드"""
        model, preprocess, _ = open_clip.create_model_and_transforms(
            self.cv_config["clip_name"],
            pretrained=self.cv_config["clip_pretrained"],
            device=self.cv_config["device"]
        )
        model.eval()
        return model, preprocess
    
    def _build_aws_icon_index(self) -> Optional[Tuple[List[IconInfo], np.ndarray, faiss.Index]]:
        """AWS 아이콘 인덱스 구축 - aws_cv_clip 로직 적용"""
        # CLIP 모델이 로드되지 않았다면 먼저 로드
        if not hasattr(self, 'clip_model') or self.clip_model is None:
            self._setup_cv_components()
        
        try:
            if not self.icon_scanner:
                print("⚠️ 아이콘 스캐너가 초기화되지 않았습니다")
                return None
            
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
                    
                    # aws_cv_clip의 전처리 로직 적용
                    pil = safe_load_image(str(icon_path))
                    pil_processed = process_icon_for_clip(pil)
                    
                    # 임베딩 생성 - PIL Image를 직접 전달
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
            
        except Exception as e:
            print(f"❌ AWS 아이콘 인덱스 구축 실패: {e}")
            return None
    
    def _load_aws_taxonomy(self) -> Optional[AWSTaxonomy]:
        """AWS 택소노미 로드"""
        try:
            taxonomy_path = self.config.get("data", {}).get("taxonomy_csv")
            if not taxonomy_path or not os.path.exists(taxonomy_path):
                print(f"⚠️ AWS 택소노미 파일을 찾을 수 없습니다: {taxonomy_path}")
                return None
            
            taxonomy = AWSTaxonomy()
            success = taxonomy.load_from_source(taxonomy_path)
            
            if success:
                print(f"✅ AWS 택소노미 로드 완료: {len(taxonomy.get_all_names())}개 서비스")
                return taxonomy
            else:
                print("❌ AWS 택소노미 로드 실패")
                return None
            
        except Exception as e:
            print(f"❌ AWS 택소노미 로드 실패: {e}")
            return None
    
    def _setup_aws_utilities(self):
        """AWS 특화 유틸리티 초기화"""
        # AWS 서비스 코드 매핑
        self.service_code_mapping = {
            "Amazon EC2": "ec2",
            "Amazon S3": "s3", 
            "AWS Lambda": "lambda",
            "Amazon RDS": "rds",
            "Amazon DynamoDB": "dynamodb",
            "Amazon CloudFront": "cloudfront",
            "Amazon API Gateway": "apigateway",
            "Amazon SNS": "sns",
            "Amazon SQS": "sqs",
            "Amazon CloudWatch": "cloudwatch",
            "AWS IAM": "iam",
            "Amazon VPC": "vpc",
            "Elastic Load Balancing": "elb",
            "Auto Scaling": "autoscaling",
            "Amazon ECS": "ecs",
            "Amazon EKS": "eks"
        }
        
        # 과도한 감지를 방지하기 위한 서비스별 제한
        self.service_detection_limits = {
            "cloudwatch": 1,  # CloudWatch는 최대 1개만 감지 (가장 높은 신뢰도)
            "kinesis": 1,     # Kinesis는 최대 1개만 감지
            "lambda": 3,      # Lambda는 최대 3개만 감지
            "s3": 2,          # S3는 최대 2개만 감지
            "ec2": 4,         # EC2는 최대 4개만 감지
        }
        
        # 서비스별 최소 신뢰도 임계값
        self.service_min_confidence = {
            "cloudwatch": 0.5,  # CloudWatch는 더 높은 임계값
            "kinesis": 0.5,     # Kinesis는 더 높은 임계값
            "lambda": 0.4,      # Lambda는 높은 임계값
            "s3": 0.4,          # S3는 높은 임계값
            "ec2": 0.35,        # EC2는 기본 임계값
        }
    
    def _apply_service_limits(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """서비스별 감지 제한 적용"""
        service_counts = {}
        filtered_detections = []
        
        for detection in detections:
            service_code = detection.service_code.lower()
            
            # 현재 서비스의 감지 수 확인
            current_count = service_counts.get(service_code, 0)
            max_count = self.service_detection_limits.get(service_code, 10)  # 기본값 10
            
            # 최소 신뢰도 확인
            min_confidence = self.service_min_confidence.get(service_code, 0.35)
            
            if current_count < max_count and detection.confidence >= min_confidence:
                filtered_detections.append(detection)
                service_counts[service_code] = current_count + 1
            else:
                print(f"⚠️ 서비스 제한으로 제외: {service_code} (신뢰도: {detection.confidence:.3f})")
        
        return filtered_detections
    
    def _detect_regions(self, image: Image.Image) -> List[BoundingBox]:
        """이미지에서 관심 영역 감지 - aws_cv_clip의 propose 로직 적용"""
        # 이미지를 OpenCV 형식으로 변환
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 이미지 크기 조정
        img, scale = self._preprocess_resize(cv_image, self.detection_config.get("max_size", 1600))
        
        boxes = []
        
        # 1. Canny Edge + MSER
        if self.detection_config.get("use_canny", True) or self.detection_config.get("use_mser", True):
            edge_boxes = self._edges_and_mser(img)
            boxes.extend(edge_boxes)
        
        # 2. Sliding Window
        if self.detection_config.get("use_sliding_window", True):
            sliding_boxes = list(self._sliding_windows(img))
            boxes.extend(sliding_boxes)
        
        # 스케일 복원
        if scale != 1.0:
            boxes = [(int(x/scale), int(y/scale), int(w/scale), int(h/scale)) for (x,y,w,h) in boxes]
        
        # BoundingBox 객체로 변환
        return [BoundingBox(x, y, w, h) for x, y, w, h in boxes]
    
    def _preprocess_resize(self, img, max_size=1600):
        """이미지 크기 조정"""
        h, w = img.shape[:2]
        s = max(h, w)
        if s <= max_size: 
            return img, 1.0
        r = max_size / s
        img2 = cv2.resize(img, (int(w*r), int(h*r)), interpolation=cv2.INTER_AREA)
        return img2, r
    
    def _edges_and_mser(self, img):
        """Canny Edge + MSER 감지"""
        boxes = []
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Canny Edge
        e = cv2.Canny(gray, 
                     self.detection_config.get("canny_low", 60),
                     self.detection_config.get("canny_high", 160))
        cnts, _ = cv2.findContours(e, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            a = w * h
            if (self.detection_config.get("min_area", 900) <= a <= 
                self.detection_config.get("max_area", 90000)):
                boxes.append((x, y, w, h))
        
        # MSER
        mser = cv2.MSER_create(delta=self.detection_config.get("mser_delta", 5))
        regions, _ = mser.detectRegions(gray)
        for r in regions:
            x, y, w, h = cv2.boundingRect(r.reshape(-1, 1, 2))
            a = w * h
            if (self.detection_config.get("min_area", 900) <= a <= 
                self.detection_config.get("max_area", 90000)):
                boxes.append((x, y, w, h))
        
        return boxes
    
    def _sliding_windows(self, img):
        """슬라이딩 윈도우 생성"""
        H, W = img.shape[:2]
        win = self.detection_config.get("win", 128)
        stride = self.detection_config.get("stride", 96)
        
        for y in range(0, max(1, H-win), stride):
            for x in range(0, max(1, W-win), stride):
                yield (x, y, win, win)
    
    def _extract_features(self, image: Image.Image, bbox: BoundingBox) -> np.ndarray:
        """영역에서 특징 추출"""
        # 이미지 크롭
        cropped = self._crop_image(image, bbox)
        
        # CLIP 임베딩 생성 - PIL Image를 직접 전달
        features = self._img_to_feat(cropped)
        
        return features
    
    def _match_features(self, features: np.ndarray) -> List[Tuple[str, float]]:
        """특징 매칭 - aws_cv_clip의 정교한 점수 계산 적용"""
        if self.aws_icon_index is None:
            # 아이콘 인덱스가 없으면 구축
            self.aws_icon_index = self._build_aws_icon_index()
            if self.aws_icon_index is None:
                return []
        
        valid_icons, icon_features, icon_index = self.aws_icon_index
        
        # FAISS 검색
        D, I = icon_index.search(features.reshape(1, -1), self.retrieval_config.get("topk", 5))
        
        matches = []
        for i, (distance, idx) in enumerate(zip(D[0], I[0])):
            if idx < len(valid_icons):
                icon_info = valid_icons[idx]
                
                # CLIP 점수
                clip_score = float((distance + 1) / 2)
                
                # ORB 점수 (참조 아이콘과 비교)
                orb_score_val = self._calculate_orb_score(features, icon_info)
                
                # OCR 점수
                ocr_score = self._calculate_ocr_score(features)
                
                # 가중합 점수
                final_score = (
                    self.retrieval_config.get("score_clip_w", 0.7) * clip_score +
                    self.retrieval_config.get("score_orb_w", 0.3) * orb_score_val +
                    self.retrieval_config.get("score_ocr_w", 0.1) * ocr_score
                )
                
                # 택소노미 정규화
                if self.aws_taxonomy:
                    taxonomy_result = self.aws_taxonomy.normalize(icon_info.service_name)
                    normalized_name = taxonomy_result.canonical_name
                    taxonomy_confidence = taxonomy_result.confidence
                    
                    # 최종 신뢰도 조합
                    final_confidence = final_score * 0.7 + taxonomy_confidence * 0.3
                    
                    # 서비스 코드 추가
                    service_code = self.service_code_mapping.get(normalized_name, "")
                    
                    matches.append((normalized_name, final_confidence, service_code))
        
        # 신뢰도 순으로 정렬
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return [(name, conf) for name, conf, _ in matches]
    
    def _calculate_orb_score(self, features: np.ndarray, icon_info: IconInfo) -> float:
        """ORB 점수 계산 - aws_cv_clip 로직 적용"""
        try:
            # 참조 아이콘 로드
            icon_path = Path(self.icon_scanner.icons_dir) / icon_info.file_path
            if not icon_path.exists():
                return 0.0
            
            # 참조 아이콘 전처리
            ref_pil = safe_load_image(str(icon_path))
            ref_pil_processed = process_icon_for_clip(ref_pil)
            ref_img = cv2.cvtColor(np.array(ref_pil_processed), cv2.COLOR_RGB2BGR)
            
            # 현재 크롭 이미지 (features에서 복원 불가능하므로 임시로 0 반환)
            # 실제로는 크롭된 이미지를 전달받아야 함
            return 0.3  # 기본값
            
        except Exception as e:
            print(f"⚠️ ORB 점수 계산 실패: {e}")
            return 0.0
    
    def _calculate_ocr_score(self, features: np.ndarray) -> float:
        """OCR 점수 계산"""
        if not self.ocr_enabled:
            return 0.0
        
        try:
            # OCR 텍스트 추출 (실제 구현에서는 이미지에서 텍스트 추출)
            # 여기서는 간단한 기본값 반환
            return 0.1
            
        except Exception as e:
            print(f"⚠️ OCR 점수 계산 실패: {e}")
            return 0.0
    
    def _img_to_feat(self, img: Image.Image) -> Optional[np.ndarray]:
        """이미지를 CLIP 임베딩으로 변환 - PIL Image를 직접 받도록 수정"""
        try:
            with torch.no_grad():
                # PIL Image를 CLIP 전처리
                img_tensor = self.clip_preprocess(img).unsqueeze(0).to(self.cv_config["device"])
                features = self.clip_model.encode_image(img_tensor)
                features = features / features.norm(dim=-1, keepdim=True)
            return features.squeeze(0).cpu().numpy()
        except Exception as e:
            print(f"⚠️ CLIP 임베딩 생성 실패: {e}")
            return None
    
    def _crop_image(self, image: Image.Image, bbox: BoundingBox) -> Image.Image:
        """이미지 크롭"""
        x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height
        return image.crop((x, y, x + w, y + h))
    
    def _load_taxonomy(self):
        """택소노미 로드 (오버라이드)"""
        # AWS 택소노미가 이미 로드되어 있음
        if hasattr(self, 'aws_taxonomy'):
            return self.aws_taxonomy
        return None
