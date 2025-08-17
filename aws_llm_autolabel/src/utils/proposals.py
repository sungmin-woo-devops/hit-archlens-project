import cv2, numpy as np
from typing import List, Tuple

def sliding_windows(h, w, win=96, stride=64):
    for y in range(0, max(1, h - win), stride):
        for x in range(0, max(1, w - win), stride):
            yield x, y, win, win

def contour_proposals(img, min_area=800, max_area=50000):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    e = cv2.Canny(gray, 50, 150)
    cnts, _ = cv2.findContours(e, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in cnts:
        x,y,w,h = cv2.boundingRect(c)
        area = w*h
        if min_area <= area <= max_area:
            boxes.append((x,y,w,h))
    return boxes

def propose_regions(img_bgr) -> List[Tuple[int,int,int,int]]:
    h, w = img_bgr.shape[:2]
    boxes = list(sliding_windows(h, w))  # coarse proposals
    boxes += contour_proposals(img_bgr)
    # optional: NMS to reduce overlaps
    return boxes
