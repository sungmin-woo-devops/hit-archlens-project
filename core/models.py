"""
Core Data Models

Hit ArchLens의 모든 모듈에서 사용하는 통합 데이터 모델
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Union
from pathlib import Path
from datetime import datetime
from enum import Enum


class CloudProvider(str, Enum):
    """클라우드 제공자 열거형"""
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    NAVER = "naver"


class AnalysisMethod(str, Enum):
    """분석 방법 열거형"""
    CV = "cv"
    LLM = "llm"
    HYBRID = "hybrid"


class DetectionStatus(str, Enum):
    """감지 상태 열거형"""
    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    UNCERTAIN = "uncertain"
    BLACKLISTED = "blacklisted"


@dataclass
class BoundingBox:
    """바운딩 박스 데이터 클래스"""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def area(self) -> int:
        """바운딩 박스 면적"""
        return self.width * self.height
    
    @property
    def center(self) -> Tuple[int, int]:
        """바운딩 박스 중심점"""
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    def to_list(self) -> List[int]:
        """리스트 형태로 변환 [x, y, width, height]"""
        return [self.x, self.y, self.width, self.height]
    
    def to_xyxy(self) -> List[int]:
        """XYXY 형태로 변환 [x1, y1, x2, y2]"""
        return [self.x, self.y, self.x + self.width, self.y + self.height]
    
    def to_xywh(self) -> List[int]:
        """XYWH 형태로 변환 [x, y, width, height]"""
        return [self.x, self.y, self.width, self.height]
    
    def intersection(self, other: 'BoundingBox') -> Optional['BoundingBox']:
        """다른 바운딩 박스와의 교집합"""
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        
        if x1 < x2 and y1 < y2:
            return BoundingBox(x1, y1, x2 - x1, y2 - y1)
        return None
    
    def union(self, other: 'BoundingBox') -> 'BoundingBox':
        """다른 바운딩 박스와의 합집합"""
        x1 = min(self.x, other.x)
        y1 = min(self.y, other.y)
        x2 = max(self.x + self.width, other.x + other.width)
        y2 = max(self.y + self.height, other.y + other.height)
        
        return BoundingBox(x1, y1, x2 - x1, y2 - y1)
    
    def iou(self, other: 'BoundingBox') -> float:
        """다른 바운딩 박스와의 IoU (Intersection over Union)"""
        intersection = self.intersection(other)
        if intersection is None:
            return 0.0
        
        intersection_area = intersection.area
        union_area = self.area + other.area - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0


@dataclass
class DetectionResult:
    """감지 결과 데이터 클래스"""
    bbox: BoundingBox
    label: str
    confidence: float
    service_code: Optional[str] = None
    canonical_name: Optional[str] = None
    cloud_provider: CloudProvider = CloudProvider.AWS
    status: DetectionStatus = DetectionStatus.DETECTED
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 검증"""
        if not isinstance(self.bbox, BoundingBox):
            # 리스트 형태로 전달된 경우 BoundingBox로 변환
            if isinstance(self.bbox, (list, tuple)) and len(self.bbox) >= 4:
                self.bbox = BoundingBox(
                    x=self.bbox[0],
                    y=self.bbox[1], 
                    width=self.bbox[2],
                    height=self.bbox[3]
                )
        
        if not isinstance(self.cloud_provider, CloudProvider):
            self.cloud_provider = CloudProvider(self.cloud_provider)
        
        if not isinstance(self.status, DetectionStatus):
            self.status = DetectionStatus(self.status)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환"""
        return {
            "bbox": self.bbox.to_list(),
            "label": self.label,
            "confidence": self.confidence,
            "service_code": self.service_code,
            "canonical_name": self.canonical_name,
            "cloud_provider": self.cloud_provider.value,
            "status": self.status.value,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetectionResult':
        """딕셔너리에서 생성"""
        bbox_data = data.get("bbox", [0, 0, 0, 0])
        if isinstance(bbox_data, list):
            bbox = BoundingBox(*bbox_data)
        else:
            bbox = bbox_data
        
        return cls(
            bbox=bbox,
            label=data.get("label", ""),
            confidence=data.get("confidence", 0.0),
            service_code=data.get("service_code"),
            canonical_name=data.get("canonical_name"),
            cloud_provider=data.get("cloud_provider", CloudProvider.AWS),
            status=data.get("status", DetectionStatus.DETECTED),
            metadata=data.get("metadata", {})
        )


@dataclass
class AnalysisResult:
    """분석 결과 데이터 클래스"""
    image_path: Union[str, Path]
    width: int
    height: int
    detections: List[DetectionResult]
    processing_time: float
    cloud_provider: CloudProvider = CloudProvider.AWS
    analysis_method: AnalysisMethod = AnalysisMethod.HYBRID
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True  # Add success field
    errors: List[str] = field(default_factory=list) # Add errors field
    
    def __post_init__(self):
        """초기화 후 검증"""
        if isinstance(self.image_path, str):
            self.image_path = Path(self.image_path)
        
        if not isinstance(self.cloud_provider, CloudProvider):
            self.cloud_provider = CloudProvider(self.cloud_provider)
        
        if not isinstance(self.analysis_method, AnalysisMethod):
            self.analysis_method = AnalysisMethod(self.analysis_method)
    
    @property
    def detection_count(self) -> int:
        """감지된 객체 수"""
        return len(self.detections)
    
    @property
    def average_confidence(self) -> float:
        """평균 신뢰도"""
        if not self.detections:
            return 0.0
        return sum(d.confidence for d in self.detections) / len(self.detections)
    
    @property
    def high_confidence_detections(self) -> List[DetectionResult]:
        """높은 신뢰도 감지 결과 (0.7 이상)"""
        return [d for d in self.detections if d.confidence >= 0.7]
    
    def filter_by_confidence(self, threshold: float) -> List[DetectionResult]:
        """신뢰도 임계값으로 필터링"""
        return [d for d in self.detections if d.confidence >= threshold]
    
    def filter_by_service(self, service_code: str) -> List[DetectionResult]:
        """서비스 코드로 필터링"""
        return [d for d in self.detections if d.service_code == service_code]
    
    @property
    def normalized_detection_count(self) -> int:
        """정규화된 감지 객체 수"""
        return sum(1 for d in self.detections if d.canonical_name and d.canonical_name != d.label)

    @property
    def normalization_success_rate(self) -> float:
        """정규화 성공률"""
        if not self.detections:
            return 0.0
        return self.normalized_detection_count / self.detection_count

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환"""
        return {
            "image_path": str(self.image_path),
            "width": self.width,
            "height": self.height,
            "detections": [d.to_dict() for d in self.detections],
            "processing_time": self.processing_time,
            "cloud_provider": self.cloud_provider.value,
            "analysis_method": self.analysis_method.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "success": self.success, # Add to_dict
            "errors": self.errors # Add to_dict
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """딕셔너리에서 생성"""
        return cls(
            image_path=data.get("image_path", ""),
            width=data.get("width", 0),
            height=data.get("height", 0),
            detections=[DetectionResult.from_dict(d) for d in data.get("detections", [])],
            processing_time=data.get("processing_time", 0.0),
            cloud_provider=data.get("cloud_provider", CloudProvider.AWS),
            analysis_method=data.get("analysis_method", AnalysisMethod.HYBRID),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            metadata=data.get("metadata", {}),
            success=data.get("success", True), # Add from_dict
            errors=data.get("errors", []) # Add from_dict
        )


@dataclass
class AWSServiceInfo:
    """AWS 서비스 정보 데이터 클래스"""
    service_code: str
    service_name: str
    category: Optional[str] = None
    icon_path: Optional[str] = None
    description: Optional[str] = None
    regions: List[str] = field(default_factory=list)
    main_resource_example: Optional[str] = None
    secondary_examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환"""
        return {
            "service_code": self.service_code,
            "service_name": self.service_name,
            "category": self.category,
            "icon_path": self.icon_path,
            "description": self.description,
            "regions": self.regions,
            "main_resource_example": self.main_resource_example,
            "secondary_examples": self.secondary_examples,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AWSServiceInfo':
        """딕셔너리에서 생성"""
        return cls(
            service_code=data.get("service_code", ""),
            service_name=data.get("service_name", ""),
            category=data.get("category"),
            icon_path=data.get("icon_path"),
            description=data.get("description"),
            regions=data.get("regions", []),
            main_resource_example=data.get("main_resource_example"),
            secondary_examples=data.get("secondary_examples", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class AWSServiceIcon:
    """AWS 서비스 아이콘 데이터 클래스"""
    group: str
    service: str
    zip_path: str
    category: Optional[str] = None
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환"""
        return {
            "group": self.group,
            "category": self.category,
            "service": self.service,
            "zip_path": self.zip_path,
            "file_path": self.file_path,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AWSServiceIcon':
        """딕셔너리에서 생성"""
        return cls(
            group=data.get("group", ""),
            category=data.get("category"),
            service=data.get("service", ""),
            zip_path=data.get("zip_path", ""),
            file_path=data.get("file_path"),
            metadata=data.get("metadata", {})
        )


@dataclass
class BatchAnalysisResult:
    """배치 분석 결과 데이터 클래스"""
    results: List[AnalysisResult]
    total_images: int
    total_detections: int
    total_processing_time: float # Add total_processing_time field
    average_processing_time: float
    success_count: int
    error_count: int
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """성공률"""
        if self.total_images == 0:
            return 0.0
        return self.success_count / self.total_images
    
    @property
    def average_detections_per_image(self) -> float:
        """이미지당 평균 감지 수"""
        if self.success_count == 0:
            return 0.0
        return self.total_detections / self.success_count
    
    @property
    def average_normalization_success_rate(self) -> float:
        """평균 정규화 성공률"""
        if not self.results:
            return 0.0
        total_rate = sum(r.normalization_success_rate for r in self.results)
        return total_rate / len(self.results)
    
    @property
    def average_confidence(self) -> float:
        """전체 감지 결과의 평균 신뢰도"""
        all_confidences = [d.confidence for ar in self.results for d in ar.detections]
        if not all_confidences:
            return 0.0
        return sum(all_confidences) / len(all_confidences)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환"""
        return {
            "results": [r.to_dict() for r in self.results],
            "total_images": self.total_images,
            "total_detections": self.total_detections,
            "total_processing_time": self.total_processing_time, # Add to_dict
            "average_processing_time": self.average_processing_time,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "average_detections_per_image": self.average_detections_per_image,
            "average_normalization_success_rate": self.average_normalization_success_rate, # 추가
            "average_confidence": self.average_confidence, # 추가
            "errors": self.errors,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchAnalysisResult':
        """딕셔너리에서 생성"""
        return cls(
            results=[AnalysisResult.from_dict(r) for r in data.get("results", [])],
            total_images=data.get("total_images", 0),
            total_detections=data.get("total_detections", 0),
            total_processing_time=data.get("total_processing_time", 0.0), # Add from_dict
            average_processing_time=data.get("average_processing_time", 0.0),
            success_count=data.get("success_count", 0),
            error_count=data.get("error_count", 0),
            errors=data.get("errors", []),
            metadata=data.get("metadata", {})
        )


# 타입 별칭들
DetectionResults = List[DetectionResult]
AnalysisResults = List[AnalysisResult]
AWSServiceInfos = List[AWSServiceInfo]
AWSServiceIcons = List[AWSServiceIcon]
