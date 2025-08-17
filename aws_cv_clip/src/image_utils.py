# aws_cv_clip/src/image_utils.py
"""
안전한 이미지 처리 유틸리티 - RGBA 모드 완전 지원
"""

from PIL import Image, ImageOps
import numpy as np
from typing import Tuple

def safe_load_image(image_path: str) -> Image.Image:
    """안전한 이미지 로딩 - 모든 모드 지원"""
    try:
        pil = Image.open(image_path)
        return pil
    except Exception as e:
        print(f"⚠️ 이미지 로딩 실패: {image_path} - {e}")
        # 기본 이미지 생성
        return Image.new('RGB', (256, 256), (255, 255, 255))

def safe_convert_to_rgba(pil: Image.Image) -> Image.Image:
    """안전한 RGBA 변환"""
    try:
        if pil.mode == 'RGBA':
            return pil
        elif pil.mode in ('RGB', 'L'):
            if pil.mode == 'L':
                pil = pil.convert('RGB')
            # 알파 채널 추가
            alpha = Image.new('L', pil.size, 255)
            pil.putalpha(alpha)
            return pil
        elif pil.mode == 'P':
            return pil.convert('RGBA')
        else:
            # 기타 모드는 RGB로 변환 후 알파 추가
            pil = pil.convert('RGB')
            alpha = Image.new('L', pil.size, 255)
            pil.putalpha(alpha)
            return pil
    except Exception as e:
        print(f"⚠️ RGBA 변환 실패: {e}")
        # 안전한 RGB 변환
        return pil.convert('RGB')

def safe_trim_transparent(pil: Image.Image) -> Image.Image:
    """안전한 투명 배경 제거 - RGBA 모드 지원"""
    try:
        if pil.mode != 'RGBA':
            pil = safe_convert_to_rgba(pil)
        
        # 투명도가 있는 경우에만 트리밍
        if pil.mode == 'RGBA':
            # 알파 채널에서 투명 영역 찾기
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
        # 투명 배경 제거
        pil = safe_trim_transparent(pil)
        
        # 패딩 계산
        w, h = pil.size
        pad = int(round(pad_ratio * max(w, h)))
        scale = (canvas_size - pad * 2) / max(w, h)
        
        # 리사이즈
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        pil_resized = pil.resize((new_w, new_h), Image.LANCZOS)
        
        # 캔버스 생성 및 중앙 배치
        canvas = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
        x = (canvas_size - new_w) // 2
        y = (canvas_size - new_h) // 2
        canvas.paste(pil_resized, (x, y), pil_resized)
        
        return canvas
    except Exception as e:
        print(f"⚠️ 정사각 패딩 실패: {e}")
        # 안전한 리사이즈
        return pil.resize((canvas_size, canvas_size), Image.LANCZOS)

def process_icon_for_clip(pil: Image.Image, canvas_size: int = 256) -> Image.Image:
    """CLIP 모델용 아이콘 전처리 - 완전 안전"""
    try:
        # 1. 안전한 RGBA 변환
        pil = safe_convert_to_rgba(pil)
        
        # 2. 투명 배경 제거
        pil = safe_trim_transparent(pil)
        
        # 3. 정사각 패딩
        pil = safe_square_pad(pil, canvas_size)
        
        # 4. 최종 RGB 변환 (CLIP 모델용)
        return pil.convert('RGB')
        
    except Exception as e:
        print(f"⚠️ 아이콘 전처리 실패: {e}")
        # 최후의 수단: 기본 RGB 이미지
        return Image.new('RGB', (canvas_size, canvas_size), (255, 255, 255))

def validate_image(pil: Image.Image) -> bool:
    """이미지 유효성 검사"""
    try:
        # 기본 검사
        if pil.size[0] <= 0 or pil.size[1] <= 0:
            return False
        
        # 모드 검사
        valid_modes = ['RGB', 'RGBA', 'L', 'P']
        if pil.mode not in valid_modes:
            return False
        
        # 데이터 검사
        pil.load()
        return True
        
    except Exception:
        return False