import pandas as pd
import re
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from rapidfuzz import process, fuzz

# 정규화를 위한 정규식 패턴들
RE_PARENS = re.compile(r"\(.*?\)")
RE_MULTI_WS = re.compile(r"\s+")
DROP_WORDS = {"service", "services", "family", "product", "products"}

@dataclass
class Taxonomy:
    canonical_to_aliases: Dict[str, List[str]]
    alias_to_canonical: Dict[str, str]
    names: List[str]
    group_mapping: Dict[str, str]
    blacklist: List[str]

    @classmethod
    def from_csv(cls, path: str, rules_dir: Optional[str] = None) -> "Taxonomy":
        """
        CSV 파일과 규칙 파일들에서 택소노미 로드
        
        Args:
            path: 택소노미 CSV 파일 경로
            rules_dir: 규칙 파일들이 있는 디렉터리 (선택적)
        """
        df = pd.read_csv(path)
        
        # 열 추론
        def pick(cols, cands):
            for c in cols:
                if c.lower() in cands: return c
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
        
        return cls(c2a, a2c, list(c2a.keys()), group_mapping, blacklist)

    def canon(self, text: str) -> str:
        """
        텍스트를 정규화된 형태로 변환
        
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

    def tokenize(self, text: str) -> List[str]:
        """
        텍스트를 토큰으로 분리
        
        Args:
            text: 토큰화할 텍스트
            
        Returns:
            List[str]: 토큰 리스트
        """
        if not isinstance(text, str): 
            return []
        
        t = text.replace("&", "and")
        t = re.sub(r"[^0-9a-zA-Z]+", " ", t)
        return [w.lower() for w in t.split() if w]

    def contains_blacklist(self, text: str) -> bool:
        """
        텍스트가 블랙리스트에 포함되는지 확인
        
        Args:
            text: 확인할 텍스트
            
        Returns:
            bool: 블랙리스트 포함 여부
        """
        key = self.canon(text)
        return any(b in key for b in self.blacklist)

    def normalize_group(self, group: str) -> str:
        """
        그룹명을 정규화
        
        Args:
            group: 정규화할 그룹명
            
        Returns:
            str: 정규화된 그룹명
        """
        if not group:
            return ""
        
        normalized = group.strip()
        return self.group_mapping.get(normalized, normalized)

    def normalize(self, s: str) -> Tuple[str, float]:
        """
        서비스명을 정규화하고 신뢰도 점수 반환
        
        Args:
            s: 정규화할 서비스명
            
        Returns:
            Tuple[str, float]: (정규화된 이름, 신뢰도 점수)
        """
        if not s:
            return "", 0.0
        
        # 정규화된 키로 검색
        key = self.canon(s)
        if key in self.alias_to_canonical:
            return self.alias_to_canonical[key], 1.0
        
        # 원본 텍스트로도 검색
        original_key = s.strip().lower()
        if original_key in self.alias_to_canonical:
            return self.alias_to_canonical[original_key], 1.0
        
        # fuzzy 매칭으로 별칭 검색
        best = process.extractOne(key, list(self.alias_to_canonical.keys()), scorer=fuzz.WRatio)
        if best:
            alias, sc, _ = best
            return self.alias_to_canonical[alias], sc/100.0
        
        # fuzzy 매칭으로 정식 이름 검색
        best2 = process.extractOne(key, self.names, scorer=fuzz.WRatio)
        if best2:
            nm, sc, _ = best2
            return nm, sc/100.0
        
        # 블랙리스트 체크
        if self.contains_blacklist(s):
            return "", 0.0
        
        return s, 0.0

    def get_aliases(self, canonical: str) -> List[str]:
        """
        정식 이름에 대한 모든 별칭 반환
        
        Args:
            canonical: 정식 서비스명
            
        Returns:
            List[str]: 별칭 리스트
        """
        return self.canonical_to_aliases.get(canonical, [])

    def get_canonical(self, alias: str) -> Optional[str]:
        """
        별칭에 대한 정식 이름 반환
        
        Args:
            alias: 별칭
            
        Returns:
            Optional[str]: 정식 이름 (없으면 None)
        """
        return self.alias_to_canonical.get(alias.lower())
