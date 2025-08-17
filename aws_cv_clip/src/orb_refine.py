# 두 이미지 간의 유사성을 ORB 알고리즘으로 측정하여 0.0에서 1.0 사이의 점수로 반환합니다. 
# 특징점 추출, 매칭, 거리 기반 필터링을 수행합니다.
import cv2, numpy as np

def orb_score(patch_bgr, icon_bgr, nfeatures=500):
    # ORB 객체 생성, 특징점 최대 개수 설정
    orb = cv2.ORB_create(nfeatures=nfeatures)
    
    # 두 이미지에서 특징점과 기술자 추출
    kp1, des1 = orb.detectAndCompute(cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2GRAY), None)
    kp2, des2 = orb.detectAndCompute(cv2.cvtColor(icon_bgr, cv2.COLOR_BGR2GRAY), None)
    
    # 유효한 기술자가 없거나 특징점이 충분하지 않으면 0.0 반환
    if des1 is None or des2 is None or len(kp1) < 5 or len(kp2) < 5:
        return 0.0
    
    # BFMatcher 객체 생성, Hamming 거리 사용
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
    # 두 이미지의 기술자 매칭
    m = bf.match(des1, des2)
    
    # 매칭 결과가 없으면 0.0 반환
    if not m:
        return 0.0
    
    # 매칭 결과를 거리 기준으로 정렬
    m = sorted(m, key=lambda x: x.distance)
    
    # 거리 기준으로 좋은 매칭 필터링
    good = [x for x in m if x.distance < 64]  # distance가 작을수록 유사
    
    # 좋은 매칭의 비율을 계산하여 0.0에서 1.0 사이의 점수 반환
    return min(1.0, len(good) / max(10, len(m)))
