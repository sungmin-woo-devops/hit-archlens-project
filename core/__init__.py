"""
Hit ArchLens Core Package

멀티 클라우드 아키텍처 분석을 위한 핵심 프레임워크
"""

__version__ = "1.0.0"
__author__ = "Hit ArchLens Team"

# 데이터 모델들
from .models import (
    BoundingBox,
    DetectionResult,
    AnalysisResult,
    AWSServiceInfo,
    AWSServiceIcon,
    BatchAnalysisResult,
    CloudProvider,
    AnalysisMethod,
    DetectionStatus
)

# 추상 클래스들
from .auto_labeler import BaseAutoLabeler
from .data_collectors import BaseDataCollector
from .taxonomy import BaseTaxonomy, TaxonomyResult, AWSTaxonomy

__all__ = [
    # 데이터 모델
    "BoundingBox",
    "DetectionResult",
    "AnalysisResult", 
    "AWSServiceInfo",
    "AWSServiceIcon",
    "BatchAnalysisResult",
    "CloudProvider",
    "AnalysisMethod",
    "DetectionStatus",
    
    # 추상 클래스
    "BaseAutoLabeler",
    "BaseDataCollector",
    "BaseTaxonomy",
    "TaxonomyResult",
    "AWSTaxonomy"
]