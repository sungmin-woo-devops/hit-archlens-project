# 이 파일은 이미지 처리 및 객체 경계 상자 제안을 위한 함수들을 포함합니다.
# - preprocess_resize: 이미지를 최대 크기에 맞춰 리사이즈
# - edges_and_mser: Canny 엣지 검출과 MSER로 윤곽선 탐지
# - sliding_windows: 이미지에서 슬라이딩 윈도우 생성
# - propose: 위 기능들을 조합하여 경계 상자 제안
import cv2, numpy as np

def preprocess_resize(img, max_size=1600):
    h, w = img.shape[:2]
    s = max(h, w)
    if s <= max_size: return img, 1.0
    r = max_size / s
    img2 = cv2.resize(img, (int(w*r), int(h*r)), interpolation=cv2.INTER_AREA)
    return img2, r

def edges_and_mser(img, canny_low=60, canny_high=160, mser_delta=5, min_area=900, max_area=90000):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    e = cv2.Canny(gray, canny_low, canny_high)
    cnts, _ = cv2.findContours(e, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in cnts:
        x,y,w,h = cv2.boundingRect(c)
        a = w*h
        if min_area <= a <= max_area:
            boxes.append((x,y,w,h))
    # MSER (문자/아이콘 내부 강한 blob)
    mser = cv2.MSER_create(delta=mser_delta)
    regions, _ = mser.detectRegions(gray)
    for r in regions:
        x,y,w,h = cv2.boundingRect(r.reshape(-1,1,2))
        a = w*h
        if min_area <= a <= max_area:
            boxes.append((x,y,w,h))
    return boxes

def sliding_windows(img, win=128, stride=96):
    H,W = img.shape[:2]
    for y in range(0, max(1, H-win), stride):
        for x in range(0, max(1, W-win), stride):
            yield (x,y,win,win)

def propose(img_bgr, cfg):
    img, r = preprocess_resize(img_bgr, cfg["max_size"])
    boxes = []
    boxes += edges_and_mser(img, cfg["canny_low"], cfg["canny_high"], cfg["mser_delta"], cfg["min_area"], cfg["max_area"])
    boxes += list(sliding_windows(img, cfg["win"], cfg["stride"]))
    # 스케일 복원
    if r != 1.0:
        boxes = [(int(x/r),int(y/r),int(w/r),int(h/r)) for (x,y,w,h) in boxes]
    return boxes
