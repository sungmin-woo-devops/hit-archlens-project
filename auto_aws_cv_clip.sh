#!/usr/bin/env bash
set -euo pipefail

# ============ Paths ============
ROOT="${PWD}/aws_cv_clip"
IMAGES_DIR="${ROOT}/images"      # 다이어그램 원본
ICONS_DIR="${ROOT}/icons"        # AWS 아이콘 템플릿 (카테고리별 PNG들)
OUT_DIR="${ROOT}/out"
TAXONOMY_CSV="/mnt/data/aws_resources_models.csv"

mkdir -p "$ROOT"/{src,$IMAGES_DIR,$ICONS_DIR,$OUT_DIR}

# ============ Config ============
cat > "${ROOT}/config.yaml" <<'YAML'
data:
  images_dir: ./images
  icons_dir: ./icons           # 각 아이콘 PNG (가능하면 흰 배경/정중앙)
  taxonomy_csv: /mnt/data/aws_resources_models.csv
model:
  clip_name: ViT-B-32           # open_clip 모델명 (경량/빠름)
  clip_pretrained: laion2b_s34b_b79k
detect:
  # 후보 탐색 파라미터 (과하면 느림 → 정확도↑ / 줄이면 빠름)
  max_size: 1600         # 긴 변 리사이즈 상한
  canny_low: 60
  canny_high: 160
  mser_delta: 5
  min_area: 900
  max_area: 90000
  win: 128               # 슬라이딩 윈도우 크기
  stride: 96
  iou_nms: 0.45
retrieval:
  topk: 5                # CLIP k-NN 후보 수
  orb_refine: true       # ORB 정합 재채점
  orb_nfeatures: 500
  score_clip_w: 0.7      # 가중합: clip 0.7 + orb 0.3 + ocr 0.1
  score_orb_w: 0.3
  score_ocr_w: 0.1
  accept_score: 0.35     # 최종 수락 임계값
ocr:
  enabled: true          # easyocr 설치되면 자동 켜짐
  lang: ["en"]           # "S3", "EC2", "RDS" 등 약어 픽업 용
output:
  dir: ./out
  format: labelstudio    # yolo | coco | labelstudio
YAML

# ============ src: Taxonomy ============
cat > "${ROOT}/src/taxonomy.py" <<'PY'
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple
from rapidfuzz import process, fuzz

@dataclass
class Taxonomy:
    canonical_to_aliases: Dict[str, List[str]]
    alias_to_canonical: Dict[str, str]
    names: List[str]

    @classmethod
    def from_csv(cls, path: str) -> "Taxonomy":
        df = pd.read_csv(path)
        # 열 추론
        def pick(cols, cands):
            for c in cols:
                if c.lower() in cands: return c
            return cols[0]
        name_col = pick(df.columns, {"canonical","name","service","label"})
        alias_col = None
        for c in df.columns:
            if c.lower() in {"aliases","alias","aka"}: alias_col = c; break

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
        return cls(c2a, a2c, list(c2a.keys()))

    def normalize(self, s: str) -> Tuple[str,float]:
        key = s.strip().lower()
        if key in self.alias_to_canonical: return self.alias_to_canonical[key], 1.0
        # alias fuzzy
        best = process.extractOne(key, list(self.alias_to_canonical.keys()), scorer=fuzz.WRatio)
        if best:
            alias, sc, _ = best
            return self.alias_to_canonical[alias], sc/100.0
        # fallback
        best2 = process.extractOne(key, self.names, scorer=fuzz.WRatio)
        if best2:
            nm, sc, _ = best2
            return nm, sc/100.0
        return s, 0.0
PY

# ============ src: Proposals (CV 후보 탐지) ============
cat > "${ROOT}/src/proposals.py" <<'PY'
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
    mser = cv2.MSER_create(_delta=mser_delta)
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
PY

# ============ src: CLIP Index ============
cat > "${ROOT}/src/clip_index.py" <<'PY'
import os, cv2, torch, faiss, numpy as np
import open_clip
from typing import List, Tuple

def load_clip(name, pretrained, device):
    model, preprocess, _ = open_clip.create_model_and_transforms(name, pretrained=pretrained, device=device)
    model.eval()
    return model, preprocess

def img_to_feat(model, preprocess, pil, device):
    with torch.no_grad():
        im = preprocess(pil).unsqueeze(0).to(device)
        f = model.encode_image(im)
        f = f / f.norm(dim=-1, keepdim=True)
    return f.squeeze(0).cpu().numpy()

def build_icon_index(icons_dir, model, preprocess, device):
    paths, feats = [], []
    for root, _, fs in os.walk(icons_dir):
        for f in fs:
            if f.lower().endswith((".png",".jpg",".jpeg",".webp")):
                p = os.path.join(root,f)
                paths.append(p)
    from PIL import Image
    for p in paths:
        pil = Image.open(p).convert("RGB")
        feats.append(img_to_feat(model, preprocess, pil, device))
    feats = np.stack(feats).astype("float32")
    idx = faiss.IndexFlatIP(feats.shape[1])
    idx.add(feats)
    return paths, feats, idx

def search(index, feats_matrix, query_feat, topk=5):
    D, I = index.search(query_feat[None,:].astype("float32"), topk)
    return D[0], I[0]
PY

# ============ src: ORB Template Refinement ============
cat > "${ROOT}/src/orb_refine.py" <<'PY'
import cv2, numpy as np

def orb_score(patch_bgr, icon_bgr, nfeatures=500):
    orb = cv2.ORB_create(nfeatures=nfeatures)
    kp1, des1 = orb.detectAndCompute(cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2GRAY), None)
    kp2, des2 = orb.detectAndCompute(cv2.cvtColor(icon_bgr, cv2.COLOR_BGR2GRAY), None)
    if des1 is None or des2 is None or len(kp1)<5 or len(kp2)<5: return 0.0
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    m = bf.match(des1, des2)
    if not m: return 0.0
    m = sorted(m, key=lambda x: x.distance)
    good = [x for x in m if x.distance < 64]   # distance 가 작을수록 유사
    return min(1.0, len(good)/max(10, len(m)))
PY

# ============ src: OCR (optional) ============
cat > "${ROOT}/src/ocr_hint.py" <<'PY'
def ocr_text(pil, lang=("en",)):
    try:
        import easyocr
        r = easyocr.Reader(list(lang), gpu=False)
        res = r.readtext(np.array(pil))
        txt = " ".join([t[1] for t in res]) if res else ""
        return txt
    except Exception:
        return ""
import numpy as np
PY

# ============ src: Exporters ============
cat > "${ROOT}/src/exporters.py" <<'PY'
import os, json

def to_labelstudio(items):
    out = []
    for it in items:
        W,H = it["width"], it["height"]
        ann = []
        for o in it["objects"]:
            x,y,w,h = o["bbox"]
            ann.append({
                "from_name":"label","to_name":"image","type":"rectanglelabels",
                "value":{
                    "x": x/W*100, "y": y/H*100, "width": w/W*100, "height": h/H*100,
                    "rectanglelabels":[o["label"]], "score": o.get("score",None)
                }
            })
        out.append({"data":{"image": os.path.basename(it["image_path"])}, "annotations":[{"result":ann}]})
    return out

def to_yolo(items, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    name2id, next_id = {}, 0
    for it in items:
        W,H = it["width"], it["height"]
        stem = os.path.splitext(os.path.basename(it["image_path"]))[0]
        lines=[]
        for o in it["objects"]:
            x,y,w,h=o["bbox"]
            cx,cy=(x+w/2)/W,(y+h/2)/H
            ww,hh=w/W,h/H
            name=o["label"]
            if name not in name2id:
                name2id[name]=next_id; next_id+=1
            cid=name2id[name]
            lines.append(f"{cid} {cx:.6f} {cy:.6f} {ww:.6f} {hh:.6f}")
        with open(os.path.join(out_dir, f"{stem}.txt"),"w") as f:
            f.write("\n".join(lines))
    with open(os.path.join(out_dir,"classes.txt"),"w") as f:
        for n,_id in sorted(name2id.items(), key=lambda x:x[1]):
            f.write(n+"\n")
PY

# ============ src: Main ============
cat > "${ROOT}/src/run.py" <<'PY'
import os, yaml, json, cv2, numpy as np
from PIL import Image
from tqdm import tqdm
from taxonomy import Taxonomy
from proposals import propose
from clip_index import load_clip, build_icon_index, img_to_feat, search
from exporters import to_labelstudio, to_yolo
from orb_refine import orb_score
from ocr_hint import ocr_text

def nms(boxes, scores, iou_thr=0.45):
    import numpy as np
    boxes = np.array(boxes, dtype=float)
    scores = np.array(scores, dtype=float)
    x1=boxes[:,0]; y1=boxes[:,1]; x2=boxes[:,0]+boxes[:,2]; y2=boxes[:,1]+boxes[:,3]
    areas=(x2-x1+1)*(y2-y1+1); order=scores.argsort()[::-1]
    keep=[]
    while order.size>0:
        i=order[0]; keep.append(i)
        xx1=np.maximum(x1[i],x1[order[1:]])
        yy1=np.maximum(y1[i],y1[order[1:]])
        xx2=np.minimum(x2[i],x2[order[1:]])
        yy2=np.minimum(y2[i],y2[order[1:]])
        w=np.maximum(0.0,xx2-xx1+1); h=np.maximum(0.0,yy2-yy1+1)
        inter=w*h; iou=inter/(areas[i]+areas[order[1:]]-inter+1e-6)
        inds=np.where(iou<=iou_thr)[0]; order=order[inds+1]
    return keep

def load_cfg():
    with open("config.yaml","r") as f:
        return yaml.safe_load(f)

def list_images(d):
    out=[]
    for r,_,fs in os.walk(d):
        for f in fs:
            if f.lower().endswith((".png",".jpg",".jpeg",".webp")):
                out.append(os.path.join(r,f))
    return sorted(out)

def main():
    cfg = load_cfg()
    os.makedirs(cfg["output"]["dir"], exist_ok=True)

    # Taxonomy
    tax = Taxonomy.from_csv(cfg["data"]["taxonomy_csv"])

    # CLIP
    import torch
    device="cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = load_clip(cfg["model"]["clip_name"], cfg["model"]["clip_pretrained"], device)
    icon_paths, icon_feats, index = build_icon_index(cfg["data"]["icons_dir"], model, preprocess, device)

    # Images
    ims = list_images(cfg["data"]["images_dir"])
    results=[]
    for p in tqdm(ims, desc="AutoLabel (CV+CLIP)"):
        img_bgr = cv2.imread(p, cv2.IMREAD_COLOR); H,W=img_bgr.shape[:2]
        boxes = propose(img_bgr, cfg["detect"])
        objects=[]
        for (x,y,w,h) in boxes:
            x0,y0,x1,y1 = max(0,x),max(0,y),min(W,x+w),min(H,y+h)
            if x1-x0<24 or y1-y0<24: continue
            crop = Image.fromarray(cv2.cvtColor(img_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))

            qf = img_to_feat(model, preprocess, crop, device)
            D, I = index.search(icon_feats, qf, topk=cfg["retrieval"]["topk"]) if False else (None, None)  # placeholder
            # 위 라인 수정: search() 시그니처 (index, feats, query_feat)
            from clip_index import search as faiss_search
            D, I = faiss_search(index, icon_feats, qf, cfg["retrieval"]["topk"])
            # clip sim ∈ [-1,1] → [0,1]
            clip_scores = [(icon_paths[i], float((d+1)/2)) for d,i in zip(D,I)]

            # ORB refine
            orb_s=0.0
            if cfg["retrieval"]["orb_refine"]:
                # 상위1 템플릿로만 정합
                best_icon = cv2.imread(clip_scores[0][0], cv2.IMREAD_COLOR)
                orb_s = orb_score(cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR), best_icon, nfeatures=cfg["retrieval"]["orb_nfeatures"])

            # OCR hint
            ocr_s = 0.0
            if cfg["ocr"]["enabled"]:
                txt = ocr_text(crop, tuple(cfg["ocr"]["lang"]))
                # 간단 가중: 텍스트가 있으면 약한 가산점
                ocr_s = 0.2 if (txt and len(txt) <= 12) else 0.0

            # 가중합
            s_clip = clip_scores[0][1]
            s = cfg["retrieval"]["score_clip_w"]*s_clip + cfg["retrieval"]["score_orb_w"]*orb_s + cfg["retrieval"]["score_ocr_w"]*ocr_s
            if s < cfg["retrieval"]["accept_score"]:
                continue

            # 라벨명: 템플릿 파일명 → taxonomy normalize
            label_raw = os.path.splitext(os.path.basename(clip_scores[0][0]))[0]
            label, nsc = tax.normalize(label_raw)

            objects.append({"bbox":[x0,y0,x1-x0,y1-y0], "label": label, "score": round(s*0.7 + nsc*0.3, 4)})

        # NMS + 정렬
        if objects:
            keep = nms([o["bbox"] for o in objects], [o["score"] for o in objects], cfg["detect"]["iou_nms"])
            objects = [objects[i] for i in keep]
            objects = sorted(objects, key=lambda o: -o["score"])

        results.append({"image_path": p, "width": W, "height": H, "objects": objects})

    # Export
    if cfg["output"]["format"] == "yolo":
        to_yolo(results, os.path.join(cfg["output"]["dir"], "yolo"))
    else:
        js = to_labelstudio(results)
        with open(os.path.join(cfg["output"]["dir"], "labelstudio.json"),"w",encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False, indent=2)
    with open(os.path.join(cfg["output"]["dir"], "raw_items.json"),"w",encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
PY

cat <<'EOM'

[사용법]
1) ./aws_cv_clip/icons/ 에 AWS 아이콘 PNG를 넣으세요.
   - 파일명 = 정규화 전 라벨 원형 (예: "Amazon-S3.png", "AWS-Lambda.png")
   - 여러 버전이 있으면 서브폴더 포함 가능 (폴더명은 무시, 파일명 기준)

2) ./aws_cv_clip/images/ 에 다이어그램 이미지를 넣으세요.

3) 실행:
   cd aws_cv_clip
   source .venv/bin/activate
   python src/run.py

4) 결과:
   - out/labelstudio.json (Label Studio 임포트)
   - out/raw_items.json (중간 산출)
   - out/yolo/* (OUT_FORMAT=yolo로 바꾸면)

[팁]
- 속도↑: config.yaml → detect.win=160, stride=128, min_area 상향
- 정확도↑: icons 템플릿을 "정면/단색" 버전으로 통일, 배경 투명 PNG 권장
- GPU가 있으면 open_clip_torch가 자동 CUDA 사용 (속도↑)
EOM