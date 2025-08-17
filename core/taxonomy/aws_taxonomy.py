"""
AWS Taxonomy Implementation

AWS 서비스 분류를 위한 구체적인 구현체 - aws_cv_clip에서 복사
"""

import pandas as pd
import re
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from rapidfuzz import process, fuzz
from dataclasses import dataclass

from .base_taxonomy import BaseTaxonomy, TaxonomyResult

# 정규화를 위한 정규식 패턴들
RE_PARENS = re.compile(r"\(.*?\)")
RE_MULTI_WS = re.compile(r"\s+")
DROP_WORDS = {"service", "services", "family", "product", "products"}


@dataclass
class AWSTaxonomyData:
    """AWS 택소노미 데이터 구조"""
    canonical_to_aliases: Dict[str, List[str]]
    alias_to_canonical: Dict[str, str]
    names: List[str]
    group_mapping: Dict[str, str]
    blacklist: List[str]


class AWSTaxonomy(BaseTaxonomy):
    """
    AWS 서비스 택소노미 구현체 - aws_cv_clip에서 복사
    
    AWS 서비스명을 정규화하고 분류하는 기능 제공
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        초기화
        
        Args:
            config: 설정 딕셔너리
        """
        super().__init__(config)
        self._data = None
    
    def load_from_source(self, source_path: str, **kwargs) -> bool:
        """
        CSV 파일과 규칙 파일들에서 택소노미 로드
        
        Args:
            source_path: 택소노미 CSV 파일 경로
            **kwargs: 추가 옵션들
                - rules_dir: 규칙 파일들이 있는 디렉터리 (선택적)
                
        Returns:
            bool: 로드 성공 여부
        """
        try:
            # aws_cv_clip의 from_csv 로직 적용
            df = pd.read_csv(source_path)
            
            # 열 추론
            def pick(cols, cands):
                for c in cols:
                    if c.lower() in cands: 
                        return c
                return cols[0]
            
            name_col = pick(df.columns, {"canonical","name","service","label"})
            alias_col = None
            for c in df.columns:
                if c.lower() in {"aliases","alias","aka"}: 
                    alias_col = c
                    break

            c2a, a2c = {}, {}
            for _, r in df.iterrows():
                canon = str(r[name_col]).strip()
                aliases = []
                if alias_col and pd.notna(r[alias_col]):
                    aliases = [a.strip() for a in str(r[alias_col]).split("|") if a.strip()]
                keys = set([canon] + aliases)
                c2a[canon] = list(keys)
                for k in keys:
                    a2c[k.lower()] = canon
            
            # 규칙 파일들 로드
            group_mapping = {}
            blacklist = []
            
            rules_dir = kwargs.get("rules_dir")
            if rules_dir:
                rules_path = Path(rules_dir)
                
                # 그룹 매핑 로드
                group_map_file = rules_path / "group_map.yaml"
                if group_map_file.exists():
                    with open(group_map_file, "r", encoding="utf-8") as f:
                        group_data = yaml.safe_load(f)
                        group_mapping = group_data.get("group_map", {})
                
                # 블랙리스트 로드
                blacklist_file = rules_path / "blacklist.yaml"
                if blacklist_file.exists():
                    with open(blacklist_file, "r", encoding="utf-8") as f:
                        blacklist_data = yaml.safe_load(f)
                        blacklist = blacklist_data.get("blacklist", [])
                
                # 별칭 규칙 로드 및 통합
                aliases_file = rules_path / "aliases.yaml"
                if aliases_file.exists():
                    with open(aliases_file, "r", encoding="utf-8") as f:
                        aliases_data = yaml.safe_load(f)
                        aliases = aliases_data.get("aliases", {})
                        
                        # 별칭을 기존 매핑에 통합
                        for alias, canonical in aliases.items():
                            if canonical in c2a:
                                c2a[canonical].append(alias)
                            else:
                                c2a[canonical] = [canonical, alias]
                            a2c[alias.lower()] = canonical
            
            # 데이터 저장
            self._data = AWSTaxonomyData(
                canonical_to_aliases=c2a,
                alias_to_canonical=a2c,
                names=list(c2a.keys()),
                group_mapping=group_mapping,
                blacklist=blacklist
            )
            
            print(f"✅ AWS 택소노미 로드 완료: {len(self._data.names)}개 서비스")
            return True
            
        except Exception as e:
            print(f"❌ AWS 택소노미 로드 실패: {e}")
            return False
    
    def normalize(self, text: str) -> TaxonomyResult:
        """
        텍스트를 정규화된 형태로 변환
        
        Args:
            text: 정규화할 텍스트
            
        Returns:
            TaxonomyResult: 정규화 결과
        """
        if not self._data:
            return TaxonomyResult(
                canonical_name="",
                confidence=0.0,
                original_text=text
            )
        
        if not text:
            return TaxonomyResult(
                canonical_name="",
                confidence=0.0,
                original_text=text
            )
        
        # aws_cv_clip의 normalize 로직 적용
        canonical, confidence = self._normalize_internal(text)
        
        return TaxonomyResult(
            canonical_name=canonical,
            confidence=confidence,
            original_text=text
        )
    
    def _normalize_internal(self, s: str) -> Tuple[str, float]:
        """
        서비스명을 정규화하고 신뢰도 점수 반환 - aws_cv_clip 로직
        
        Args:
            s: 정규화할 서비스명
            
        Returns:
            Tuple[str, float]: (정규화된 이름, 신뢰도 점수)
        """
        if not s:
            return "", 0.0
        
        # 정규화된 키로 검색
        key = self._canon(s)
        if key in self._data.alias_to_canonical:
            return self._data.alias_to_canonical[key], 1.0
        
        # 원본 텍스트로도 검색
        original_key = s.strip().lower()
        if original_key in self._data.alias_to_canonical:
            return self._data.alias_to_canonical[original_key], 1.0
        
        # fuzzy 매칭으로 별칭 검색
        best = process.extractOne(key, list(self._data.alias_to_canonical.keys()), scorer=fuzz.WRatio)
        if best:
            alias, sc, _ = best
            return self._data.alias_to_canonical[alias], sc/100.0
        
        # fuzzy 매칭으로 정식 이름 검색
        best2 = process.extractOne(key, self._data.names, scorer=fuzz.WRatio)
        if best2:
            nm, sc, _ = best2
            return nm, sc/100.0
        
        # 블랙리스트 체크
        if self._contains_blacklist(s):
            return "", 0.0
        
        return s, 0.0
    
    def _canon(self, text: str) -> str:
        """
        텍스트를 정규화된 형태로 변환 - aws_cv_clip 로직
        
        Args:
            text: 정규화할 텍스트
            
        Returns:
            str: 정규화된 텍스트
        """
        if not isinstance(text, str): 
            return ""
        
        # 괄호 제거
        t = RE_PARENS.sub("", text)
        
        # Amazon/AWS 접두사 제거
        t = re.sub(r"^(amazon|aws)\s+", "", t, flags=re.I)
        
        # 특수문자 정규화
        t = t.replace("&", "and").replace("–", "-").replace("—", "-")
        t = t.replace("-", " ").replace("_", " ").replace("/", " ")
        
        # 토큰화 및 불용어 제거
        tokens = [w for w in re.split(r"\s+", t) if w]
        tokens = [w for w in tokens if w.lower() not in DROP_WORDS]
        
        # 최종 정규화
        t = " ".join(tokens)
        t = RE_MULTI_WS.sub(" ", t).strip().lower()
        
        return t
    
    def _contains_blacklist(self, text: str) -> bool:
        """
        텍스트가 블랙리스트에 포함되는지 확인
        
        Args:
            text: 확인할 텍스트
            
        Returns:
            bool: 블랙리스트 포함 여부
        """
        if not self._data:
            return False
        
        key = self._canon(text)
        return any(b in key for b in self._data.blacklist)
    
    def get_all_names(self) -> List[str]:
        """모든 정규화된 이름 반환"""
        if not self._data:
            return []
        return self._data.names
    
    def validate(self) -> Tuple[bool, List[str]]:
        """택소노미 유효성 검증"""
        errors = []
        
        if not self._data:
            errors.append("택소노미 데이터가 로드되지 않았습니다")
            return False, errors
        
        if not self._data.names:
            errors.append("정규화된 이름이 없습니다")
        
        if not self._data.alias_to_canonical:
            errors.append("별칭 매핑이 없습니다")
        
        return len(errors) == 0, errors
