"""
Base Data Collector Module

클라우드 데이터 수집을 위한 추상 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from ..models import CloudProvider


@dataclass
class CollectionResult:
    """데이터 수집 결과"""
    success: bool
    data_count: int
    processing_time: float
    output_paths: List[str]
    errors: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CollectionStatistics:
    """수집 통계 정보"""
    total_collections: int
    successful_collections: int
    failed_collections: int
    total_data_count: int
    total_processing_time: float
    collection_details: Dict[str, CollectionResult]
    
    @property
    def success_rate(self) -> float:
        """성공률"""
        if self.total_collections == 0:
            return 0.0
        return self.successful_collections / self.total_collections
    
    @property
    def average_processing_time(self) -> float:
        """평균 처리 시간"""
        if self.successful_collections == 0:
            return 0.0
        return self.total_processing_time / self.successful_collections


class BaseDataCollector(ABC):
    """
    데이터 수집 베이스 클래스
    
    모든 클라우드 제공자별 데이터 수집기가 상속해야 하는 추상 클래스
    """
    
    def __init__(self, cloud_provider: Union[CloudProvider, str], config: Dict[str, Any]):
        """
        초기화
        
        Args:
            cloud_provider: 클라우드 제공자
            config: 설정 딕셔너리
        """
        self.cloud_provider = CloudProvider(cloud_provider) if isinstance(cloud_provider, str) else cloud_provider
        self.config = config
        self.output_dir = Path(config.get("output_dir", "data"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 수집 통계
        self.collection_stats = CollectionStatistics(
            total_collections=0,
            successful_collections=0,
            failed_collections=0,
            total_data_count=0,
            total_processing_time=0.0,
            collection_details={}
        )
        
        print(f"✅ {self.cloud_provider.value.upper()} 데이터 수집기 초기화 완료")
    
    @abstractmethod
    def collect(self) -> CollectionResult:
        """
        데이터 수집 실행
        
        Returns:
            CollectionResult: 수집 결과
        """
        pass
    
    @abstractmethod
    def validate_data(self, data: Any) -> bool:
        """
        수집된 데이터 검증
        
        Args:
            data: 검증할 데이터
            
        Returns:
            bool: 유효성 여부
        """
        pass
    
    @abstractmethod
    def get_supported_data_types(self) -> List[str]:
        """
        지원하는 데이터 타입 목록 반환
        
        Returns:
            List[str]: 지원하는 데이터 타입 목록
        """
        pass
    
    def collect_all(self) -> CollectionStatistics:
        """
        모든 지원 데이터 타입 수집
        
        Returns:
            CollectionStatistics: 전체 수집 통계
        """
        supported_types = self.get_supported_data_types()
        
        for data_type in supported_types:
            try:
                result = self.collect_specific(data_type)
                self.collection_stats.collection_details[data_type] = result
                self.collection_stats.total_collections += 1
                
                if result.success:
                    self.collection_stats.successful_collections += 1
                    self.collection_stats.total_data_count += result.data_count
                    self.collection_stats.total_processing_time += result.processing_time
                else:
                    self.collection_stats.failed_collections += 1
                    
            except Exception as e:
                error_result = CollectionResult(
                    success=False,
                    data_count=0,
                    processing_time=0.0,
                    output_paths=[],
                    errors=[str(e)]
                )
                self.collection_stats.collection_details[data_type] = error_result
                self.collection_stats.total_collections += 1
                self.collection_stats.failed_collections += 1
                print(f"❌ {data_type} 수집 실패: {e}")
        
        return self.collection_stats
    
    def collect_specific(self, data_type: str) -> CollectionResult:
        """
        특정 데이터 타입 수집
        
        Args:
            data_type: 수집할 데이터 타입
            
        Returns:
            CollectionResult: 수집 결과
        """
        if data_type not in self.get_supported_data_types():
            return CollectionResult(
                success=False,
                data_count=0,
                processing_time=0.0,
                output_paths=[],
                errors=[f"지원하지 않는 데이터 타입: {data_type}"]
            )
        
        # 하위 클래스에서 구현
        return self._collect_specific_impl(data_type)
    
    @abstractmethod
    def _collect_specific_impl(self, data_type: str) -> CollectionResult:
        """
        특정 데이터 타입 수집 구현 (하위 클래스에서 구현)
        
        Args:
            data_type: 수집할 데이터 타입
            
        Returns:
            CollectionResult: 수집 결과
        """
        pass
    
    def get_collection_status(self) -> Dict[str, Any]:
        """
        수집 상태 정보 반환
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        return {
            "cloud_provider": self.cloud_provider.value,
            "total_collections": self.collection_stats.total_collections,
            "successful_collections": self.collection_stats.successful_collections,
            "failed_collections": self.collection_stats.failed_collections,
            "success_rate": self.collection_stats.success_rate,
            "total_data_count": self.collection_stats.total_data_count,
            "average_processing_time": self.collection_stats.average_processing_time,
            "supported_data_types": self.get_supported_data_types()
        }
    
    def reset_statistics(self) -> None:
        """수집 통계 초기화"""
        self.collection_stats = CollectionStatistics(
            total_collections=0,
            successful_collections=0,
            failed_collections=0,
            total_data_count=0,
            total_processing_time=0.0,
            collection_details={}
        )
    
    def export_statistics(self, output_path: Union[str, Path]) -> bool:
        """
        수집 통계 내보내기
        
        Args:
            output_path: 출력 파일 경로
            
        Returns:
            bool: 내보내기 성공 여부
        """
        try:
            import json
            
            stats_data = {
                "timestamp": datetime.now().isoformat(),
                "cloud_provider": self.cloud_provider.value,
                "statistics": {
                    "total_collections": self.collection_stats.total_collections,
                    "successful_collections": self.collection_stats.successful_collections,
                    "failed_collections": self.collection_stats.failed_collections,
                    "success_rate": self.collection_stats.success_rate,
                    "total_data_count": self.collection_stats.total_data_count,
                    "average_processing_time": self.collection_stats.average_processing_time
                },
                "collection_details": {
                    data_type: {
                        "success": result.success,
                        "data_count": result.data_count,
                        "processing_time": result.processing_time,
                        "output_paths": result.output_paths,
                        "errors": result.errors
                    }
                    for data_type, result in self.collection_stats.collection_details.items()
                }
            }
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 통계 내보내기 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 통계 내보내기 실패: {e}")
            return False
