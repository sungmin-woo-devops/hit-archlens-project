# aws_cv_clip/src/icon_scanner.py
"""
AWS 아이콘 스캐너 - 핵심 기능 중심으로 리팩토링
PNG 전용, 최대 사이즈 선택, RGBA 안전 처리
"""

import os
import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class IconInfo:
    """아이콘 정보 데이터 클래스"""
    file_path: str
    service_name: str
    service_code: str
    category: str
    size: int
    confidence: float

class IconScanner:
    """AWS 아이콘 스캐너 - 핵심 기능만 포함"""
    
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
        """파일명에서 서비스명 추출 - 핵심 로직만"""
        name = Path(filename).stem
        
        # 패턴 매칭 (간소화)
        if "Resource-Icons" in icon_type:
            pattern = r'Res_([A-Za-z0-9-]+)'
        else:
            pattern = r'Arch_([A-Za-z0-9-]+)'
        
        match = re.search(pattern, name)
        if match:
            service_code = match.group(1).lower()
            # 정확한 매칭
            if service_code in self.service_mapping:
                return self.service_mapping[service_code], 0.9
            # 부분 매칭
            for code, name in self.service_mapping.items():
                if service_code in code or code in service_code:
                    return name, 0.7
        
        return "Unknown", 0.0
    
    def _extract_size(self, filename: str) -> int:
        """사이즈 추출 - 핵심 로직만"""
        match = re.search(r'_(\d+)', filename)
        return int(match.group(1)) if match else 32
    
    def _extract_category(self, file_path: str) -> str:
        """카테고리 추출"""
        parts = Path(file_path).parts
        return parts[1] if len(parts) > 1 else "Unknown"
    
    def _find_service_code(self, service_name: str) -> str:
        """서비스명으로 코드 찾기"""
        for code, name in self.service_mapping.items():
            if name == service_name:
                return code
        return ""

def main():
    """테스트 실행"""
    scanner = IconScanner("./icons", "./aws_resources_models.csv")
    icons = scanner.scan_icons()
    
    print(f"\n�� 스캔 결과:")
    print(f"총 아이콘: {len(icons)}개")
    
    # 사이즈별 통계
    size_stats = defaultdict(int)
    for icon in icons:
        size_stats[icon.size] += 1
    
    print(f"\n�� 사이즈별 분포:")
    for size in sorted(size_stats.keys()):
        print(f"  {size}px: {size_stats[size]}개")

if __name__ == "__main__":
    main()