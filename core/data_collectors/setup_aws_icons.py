"""
AWS 아이콘 설정 스크립트
aws_cv_clip의 아이콘을 core 모듈이 사용할 수 있도록 복사
"""

import shutil
from pathlib import Path

def setup_aws_icons():
    """AWS 아이콘 설정"""
    source_dir = Path("aws_cv_clip/icons")
    target_dir = Path("out/aws/icons")
    
    if not source_dir.exists():
        print(f"❌ 소스 아이콘 디렉터리를 찾을 수 없습니다: {source_dir}")
        return False
    
    # 타겟 디렉터리 생성
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 아이콘 복사
    try:
        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
        print(f"✅ AWS 아이콘 복사 완료: {target_dir}")
        return True
    except Exception as e:
        print(f"❌ AWS 아이콘 복사 실패: {e}")
        return False

if __name__ == "__main__":
    setup_aws_icons()
