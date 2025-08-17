"""
Base Taxonomy Module

클라우드 서비스 분류를 위한 추상 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TaxonomyResult:
    """택소노미 정규화 결과"""
    canonical_name: str
    confidence: float
    original_text: str
    metadata: Optional[Dict[str, Any]] = None


class BaseTaxonomy(ABC):
    """
    택소노미 베이스 클래스
    
    모든 클라우드 제공자별 택소노미 구현체가 상속해야 하는 추상 클래스
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        초기화
        
        Args:
            config: 설정 딕셔너리
        """
        self.config = config or {}
        self._names = set()
        self._aliases = {}
        self._rules = {}
        
    @abstractmethod
    def load_from_source(self, source_path: str, **kwargs) -> bool:
        """
        소스에서 택소노미 로드
        
        Args:
            source_path: 소스 파일 경로
            **kwargs: 추가 옵션들
            
        Returns:
            bool: 로드 성공 여부
        """
        pass
    
    @abstractmethod
    def normalize(self, text: str) -> TaxonomyResult:
        """
        텍스트를 정규화된 형태로 변환
        
        Args:
            text: 정규화할 텍스트
            
        Returns:
            TaxonomyResult: 정규화 결과
        """
        pass
    
    @abstractmethod
    def validate(self) -> Tuple[bool, List[str]]:
        """
        택소노미 유효성 검증
        
        Returns:
            Tuple[bool, List[str]]: (유효성 여부, 오류 메시지 리스트)
        """
        pass
    
    def get_all_names(self) -> List[str]:
        """모든 정규화된 이름 반환"""
        return list(self._names)
    
    def get_aliases(self, canonical_name: str) -> List[str]:
        """특정 정규화된 이름의 별칭들 반환"""
        return self._aliases.get(canonical_name, [])
    
    def add_name(self, name: str):
        """정규화된 이름 추가"""
        self._names.add(name)
    
    def add_alias(self, canonical_name: str, alias: str):
        """별칭 추가"""
        if canonical_name not in self._aliases:
            self._aliases[canonical_name] = []
        self._aliases[canonical_name].append(alias)
    
    def add_rule(self, rule_name: str, rule_data: Dict[str, Any]):
        """규칙 추가"""
        self._rules[rule_name] = rule_data
