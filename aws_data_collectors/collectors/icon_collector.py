"""
AWS 아이콘 수집기
AWS 공식 아이콘 ZIP 파일을 파싱하여 매핑 파일을 생성합니다.
"""

import csv
import json
import pathlib
import re
import zipfile
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class IconMapping:
    """아이콘 매핑 데이터 클래스"""
    group: str
    category: Optional[str]
    service: str
    zip_path: str
    file_name: str
    size: Optional[str] = None
    theme: Optional[str] = None

class AWSIconCollector:
    """
    AWS 아이콘 수집기
    
    AWS 공식 아이콘 ZIP 파일을 파싱하여 구조화된 매핑 정보를 생성합니다.
    
    사용 예시:
    ```python
    collector = AWSIconCollector()
    mappings = collector.collect_icons("Asset-Package.zip")
    collector.save_mappings(mappings, "output.csv", "output.json")
    ```
    """
    
    def __init__(self):
        # 정규식 패턴
        self.suffix_pattern = re.compile(r"(_?(Dark|Light))?(_?\d{2})?(\.svg|\.png)$", re.I)
        
        # ZIP 구조 상 고정된 루트
        self.res_root_hint = "Resource-Icons_"
        self.res_dir_prefix = "Res_"
        self.service_file_prefix = "Res_"
        
        # 그룹 표준화 (공식 명칭과 폴더명 차이 보정)
        self.group_normalize = {
            "Networking Content Delivery": "Networking & Content Delivery",
            "Security Identity Compliance": "Security, Identity, & Compliance",
            "Management Governance": "Management & Governance",
            "Application Integration": "Application Integration",
            "Developer Tools": "Developer Tools",
            "Front End Web Mobile": "Front-End Web & Mobile",
            "End User Computing": "End User Computing",
            "Machine Learning": "Machine Learning",
            "Quantum Technologies": "Quantum Technologies",
            "Migration Modernization": "Migration & Modernization",
        }
    
    def normalize_spaces(self, s: str) -> str:
        """공백 정규화"""
        return re.sub(r"\s+", " ", s).strip()
    
    def normalize_group(self, folder_name: str) -> Optional[str]:
        """폴더명을 그룹명으로 정규화"""
        name = folder_name
        if name.startswith(self.res_dir_prefix):
            name = name[len(self.res_dir_prefix):]
        name = name.replace("-", " ")
        name = self.normalize_spaces(name)
        return self.group_normalize.get(name, name)
    
    def normalize_service_from_file(self, stem: str) -> str:
        """파일명에서 서비스명 추출"""
        s = stem
        if s.startswith(self.service_file_prefix):
            s = s[len(self.service_file_prefix):]
        # 서비스 기본명은 첫 '_' 이전
        base = s.split("_", 1)[0]
        base = base.replace("-", " ")
        base = self.normalize_spaces(base)
        return base
    
    def extract_icon_metadata(self, file_path: str) -> Dict[str, Optional[str]]:
        """파일 경로에서 아이콘 메타데이터 추출"""
        file_name = pathlib.Path(file_path).name
        stem = pathlib.Path(file_path).stem
        
        # 사이즈와 테마 추출
        match = self.suffix_pattern.search(file_name)
        size = None
        theme = None
        
        if match:
            theme_match = match.group(2)  # Dark/Light
            size_match = match.group(3)   # 숫자
            if theme_match:
                theme = theme_match
            if size_match:
                size = size_match.strip("_")
        
        return {
            "file_name": file_name,
            "size": size,
            "theme": theme,
            "stem": stem
        }
    
    def is_icon_file(self, file_path: str) -> bool:
        """아이콘 파일인지 확인"""
        p = file_path.lower()
        return p.endswith((".svg", ".png"))
    
    def collect_icons(self, zip_path: str) -> List[IconMapping]:
        """
        ZIP 파일에서 아이콘 매핑 정보 수집
        
        Args:
            zip_path: AWS 아이콘 패키지 ZIP 파일 경로
            
        Returns:
            List[IconMapping]: 아이콘 매핑 정보 리스트
        """
        mappings = []
        
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            
            for file_path in names:
                if not self.is_icon_file(file_path):
                    continue
                
                parts = pathlib.PurePosixPath(file_path).parts
                if not any(self.res_root_hint in p for p in parts):
                    continue  # 리소스 아이콘만 사용
                
                if len(parts) < 3:
                    continue
                
                group_folder = parts[-2]  # e.g., "Res_Security-Identity-Compliance"
                service_file = parts[-1]  # e.g., "Res_Amazon-EC2_Instance_48.svg"
                
                group = self.normalize_group(group_folder)
                metadata = self.extract_icon_metadata(file_path)
                stem = self.suffix_pattern.sub("", service_file)  # 사이즈/테마/확장자 제거
                stem = stem.rsplit(".", 1)[0] if "." in stem else stem
                
                service = self.normalize_service_from_file(stem)
                
                # 잡음/유틸 제거
                if len(service) < 2 or service.lower() in {"learn more", "pricing", "faq"}:
                    continue
                
                mapping = IconMapping(
                    group=group or "",
                    category=None,
                    service=service,
                    zip_path=file_path,
                    file_name=metadata["file_name"],
                    size=metadata["size"],
                    theme=metadata["theme"]
                )
                mappings.append(mapping)
        
        # 중복 제거
        seen = set()
        unique_mappings = []
        for mapping in mappings:
            key = (mapping.group, mapping.category, mapping.service)
            if key not in seen:
                seen.add(key)
                unique_mappings.append(mapping)
        
        return unique_mappings
    
    def save_mappings(self, mappings: List[IconMapping], 
                     csv_path: str, json_path: str) -> None:
        """
        매핑 정보를 CSV와 JSON 파일로 저장
        
        Args:
            mappings: 아이콘 매핑 정보 리스트
            csv_path: CSV 출력 파일 경로
            json_path: JSON 출력 파일 경로
        """
        # CSV 저장
        with open(csv_path, "w", newline="", encoding="utf-8") as fp:
            w = csv.writer(fp)
            w.writerow(["group", "category", "service", "zip_path", "file_name", "size", "theme"])
            for mapping in mappings:
                w.writerow([
                    mapping.group,
                    mapping.category,
                    mapping.service,
                    mapping.zip_path,
                    mapping.file_name,
                    mapping.size,
                    mapping.theme
                ])
        
        # JSON 저장
        json_data = []
        for mapping in mappings:
            json_data.append({
                "group": mapping.group,
                "category": mapping.category,
                "service": mapping.service,
                "zip_path": mapping.zip_path,
                "file_name": mapping.file_name,
                "size": mapping.size,
                "theme": mapping.theme
            })
        
        with open(json_path, "w", encoding="utf-8") as fp:
            json.dump(json_data, fp, ensure_ascii=False, indent=2)
        
        print(f"[OK] CSV: {csv_path}  rows={len(mappings)}")
        print(f"[OK] JSON: {json_path}  rows={len(mappings)}")
    
    def get_statistics(self, mappings: List[IconMapping]) -> Dict:
        """매핑 정보 통계"""
        stats = {
            "total_icons": len(mappings),
            "groups": {},
            "services": {},
            "sizes": {},
            "themes": {}
        }
        
        for mapping in mappings:
            # 그룹별 통계
            stats["groups"][mapping.group] = stats["groups"].get(mapping.group, 0) + 1
            
            # 서비스별 통계
            stats["services"][mapping.service] = stats["services"].get(mapping.service, 0) + 1
            
            # 사이즈별 통계
            if mapping.size:
                stats["sizes"][mapping.size] = stats["sizes"].get(mapping.size, 0) + 1
            
            # 테마별 통계
            if mapping.theme:
                stats["themes"][mapping.theme] = stats["themes"].get(mapping.theme, 0) + 1
        
        return stats
