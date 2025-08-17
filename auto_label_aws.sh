#!/usr/bin/env bash
set -euo pipefail

# =========================
# Auto Labeling for AWS Icons in Architecture Diagrams
# - Modes:
#   A) full_image_llm : Whole-image -> LLM detects (bboxes + classes) in one shot
#   B) patch_llm      : Region proposals -> LLM suggests names -> taxonomy normalize
# - Outputs: YOLO TXT, COCO JSON, Label Studio JSON
# =========================

# --------- User Config (quick toggles) ----------
PROJECT_DIR="${PWD}/aws_llm_autolabel"
IMAGES_DIR="${PROJECT_DIR}/images"
URL_LIST="${PROJECT_DIR}/images.txt"            # optional: image URLs
TAXONOMY_CSV="/mnt/data/aws_resources_models.csv"  # provided by user
MODE="${MODE:-full_image_llm}"                  # full_image_llm | patch_llm
PROVIDER="${PROVIDER:-openai}"                  # openai | deepseek
OPENAI_MODEL_VISION="${OPENAI_MODEL_VISION:-gpt-4o-mini}"   # or gpt-4.1, gpt-4o
OPENAI_MODEL_EMBED="${OPENAI_MODEL_EMBED:-text-embedding-3-large}"
DEEPSEEK_MODEL_VISION="${DEEPSEEK_MODEL_VISION:-deepseek-vl-1.5}"  # example
MAX_WORKERS="${MAX_WORKERS:-4}"
OUT_FORMAT="${OUT_FORMAT:-labelstudio}"         # yolo | coco | labelstudio
CONF_THRESHOLD="${CONF_THRESHOLD:-0.35}"

echo "[+] Project: ${PROJECT_DIR}"
mkdir -p "${PROJECT_DIR}/src" "${PROJECT_DIR}/out" "${IMAGES_DIR}"

# --------- Python env ----------
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3가 필요합니다."; exit 1
fi
python3 -m venv "${PROJECT_DIR}/.venv"
source "${PROJECT_DIR}/.venv/bin/activate"
pip install -U pip >/dev/null

pip install \
  openai \
  requests \
  numpy \
  pandas \
  pillow \
  opencv-python-headless \
  tqdm \
  rapidfuzz \
  pydantic \
  pyyaml >/dev/null

# --------- Config ----------
cat > "${PROJECT_DIR}/config.yaml" <<'YAML'
project_name: aws_llm_autolabel
provider: ${PROVIDER}         # openai | deepseek (env-var expanded at runtime)
mode: ${MODE}                  # full_image_llm | patch_llm
openai:
  vision_model: ${OPENAI_MODEL_VISION}
  embed_model: ${OPENAI_MODEL_EMBED}
deepseek:
  vision_model: ${DEEPSEEK_MODEL_VISION}
data:
  images_dir: ./images
  url_list: ./images.txt       # optional
  taxonomy_csv: /mnt/data/aws_resources_models.csv
runtime:
  max_workers: ${MAX_WORKERS}
  conf_threshold: ${CONF_THRESHOLD}
output:
  dir: ./out
  format: ${OUT_FORMAT}        # yolo | coco | labelstudio
YAML

# --------- Core: taxonomy loader & normalizer ----------
cat > "${PROJECT_DIR}/src/taxonomy.py" <<'PY'
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
        """
        Expect CSV columns like:
          canonical,aliases
        where aliases is '|' separated optional list
        If your CSV has different columns (e.g., 'service','family', etc),
        tweak the parsing below accordingly.
        """
        df = pd.read_csv(path)
        # Heuristics: find best columns
        cols = [c.lower() for c in df.columns]
        try:
            name_col = next(c for c in df.columns if c.lower() in ("canonical","name","service","label"))
        except StopIteration:
            name_col = df.columns[0]
        alias_col = None
        for c in df.columns:
            if c.lower() in ("aliases","alias","aka"):
                alias_col = c
                break

        canonical_to_aliases = {}
        alias_to_canonical = {}

        for _, row in df.iterrows():
            canon = str(row[name_col]).strip()
            aliases = []
            if alias_col and not pd.isna(row[alias_col]):
                aliases = [a.strip() for a in str(row[alias_col]).split("|") if a.strip()]
            all_keys = set([canon] + aliases)
            canonical_to_aliases[canon] = list(all_keys)
            for k in all_keys:
                alias_to_canonical[k.lower()] = canon

        names = list(canonical_to_aliases.keys())
        return cls(canonical_to_aliases, alias_to_canonical, names)

    def normalize(self, s: str) -> Tuple[str, float]:
        """Map arbitrary text to canonical via fuzzy matching + alias map."""
        key = s.strip().lower()
        if key in self.alias_to_canonical:
            return self.alias_to_canonical[key], 1.0
        # fuzzy to all aliases
        best = process.extractOne(
            key,
            list(self.alias_to_canonical.keys()),
            scorer=fuzz.WRatio
        )
        if best:
            alias, score, _ = best
            return self.alias_to_canonical[alias], score/100.0
        # fallback to canonical names
        best2 = process.extractOne(
            key, self.names, scorer=fuzz.WRatio
        )
        if best2:
            name, score, _ = best2
            return name, score/100.0
        return s, 0.0
PY

# --------- Simple region proposals (for patch_llm) ----------
cat > "${PROJECT_DIR}/src/proposals.py" <<'PY'
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
PY

# --------- LLM calls (OpenAI / DeepSeek) ----------
cat > "${PROJECT_DIR}/src/llm.py" <<'PY'
import base64, io, os, json, time
from typing import List, Dict, Any, Optional
from PIL import Image
import requests

OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEEPSEEK_BASE = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

def pil_to_b64(pil_img: Image.Image) -> str:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def call_openai_vision(image_pil: Image.Image, prompt: str, model: str) -> str:
    import openai
    client = openai.OpenAI(base_url=OPENAI_BASE, api_key=os.getenv("OPENAI_API_KEY"))
    b64 = pil_to_b64(image_pil)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content":"You are a precise vision annotator. Return strictly valid JSON."},
            {"role":"user","content":[
                {"type":"text","text":prompt},
                {"type":"image_url","image_url":{"url": f"data:image/png;base64,{b64}"}}
            ]}
        ],
        temperature=0
    )
    return resp.choices[0].message.content

def call_deepseek_vision(image_pil: Image.Image, prompt: str, model: str) -> str:
    # Generic VL endpoint; adjust to DeepSeek's latest if needed
    b64 = pil_to_b64(image_pil)
    headers = {
        "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role":"system","content":"You are a precise vision annotator. Return strictly valid JSON."},
            {"role":"user","content":[
                {"type":"text","text":prompt},
                {"type":"image_url","image_url":{"url": f"data:image/png;base64,{b64}"}}
            ]}
        ],
        "temperature": 0
    }
    r = requests.post(f"{DEEPSEEK_BASE}/chat/completions", headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]
PY

# --------- Embedding helper (OpenAI only; optional) ----------
cat > "${PROJECT_DIR}/src/embeds.py" <<'PY'
import os
from typing import List
def embed_texts(texts: List[str], model: str) -> List[List[float]]:
    # Optional refinement step; if no OPENAI key, skip in caller.
    import openai
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    out = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in out.data]
PY

# --------- IO utils ----------
cat > "${PROJECT_DIR}/src/io_utils.py" <<'PY'
import os, json, hashlib, shutil
from typing import List, Dict, Any
from PIL import Image
import requests

def ensure_dir(p): os.makedirs(p, exist_ok=True)

def download_images(url_list_path: str, out_dir: str):
    ensure_dir(out_dir)
    if not os.path.exists(url_list_path): return
    with open(url_list_path, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if not url: continue
            h = hashlib.md5(url.encode()).hexdigest()[:10]
            fn = os.path.join(out_dir, f"{h}.png")
            if os.path.exists(fn): continue
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(fn, "wb") as w:
                w.write(r.content)

def list_images(dir_path: str) -> List[str]:
    exts = (".png",".jpg",".jpeg",".webp",".bmp")
    files = []
    for root, _, fs in os.walk(dir_path):
        for f in fs:
            if f.lower().endswith(exts):
                files.append(os.path.join(root, f))
    return sorted(files)

def load_image(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")

def save_json(path: str, data: Any):
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
PY

# --------- Annotation exporters ----------
cat > "${PROJECT_DIR}/src/exporters.py" <<'PY'
import os, json
from typing import List, Dict, Any
from io import BytesIO

def to_labelstudio(items: List[dict]) -> dict:
    """
    items: list of dict per image
      { "image_path":..., "width":..., "height":...,
        "objects":[ {"bbox":[x,y,w,h], "label": "Amazon S3", "score":0.88}, ...] }
    """
    out = []
    for it in items:
        img_rel = os.path.basename(it["image_path"])
        anns = []
        for obj in it.get("objects", []):
            x,y,w,h = obj["bbox"]
            anns.append({
                "from_name":"label",
                "to_name":"image",
                "type":"rectanglelabels",
                "value":{
                    "x": x/it["width"]*100,
                    "y": y/it["height"]*100,
                    "width": w/it["width"]*100,
                    "height": h/it["height"]*100,
                    "rectanglelabels":[obj["label"]],
                    "score": obj.get("score", None)
                }
            })
        out.append({
            "data":{"image": img_rel},
            "annotations":[{"result": anns}]
        })
    return out

def to_yolo(items: List[dict], out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    name_to_id = {}
    next_id = 0
    for it in items:
        w, h = it["width"], it["height"]
        label_path = os.path.join(out_dir, os.path.splitext(os.path.basename(it["image_path"]))[0] + ".txt")
        lines = []
        for obj in it.get("objects", []):
            x,y,bw,bh = obj["bbox"]
            cx = (x + bw/2)/w
            cy = (y + bh/2)/h
            ww = bw/w
            hh = bh/h
            name = obj["label"]
            if name not in name_to_id:
                name_to_id[name] = next_id; next_id += 1
            cls_id = name_to_id[name]
            lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {ww:.6f} {hh:.6f}")
        with open(label_path,"w") as f:
            f.write("\n".join(lines))
    # also export classes.txt
    with open(os.path.join(out_dir,"classes.txt"),"w") as f:
        for name,_id in sorted(name_to_id.items(), key=lambda x:x[1]):
            f.write(f"{name}\n")

def to_coco(items: List[dict]) -> dict:
    images, annotations, categories = [], [], []
    name_to_id = {}
    for img_id, it in enumerate(items, start=1):
        images.append({
            "id": img_id,
            "file_name": os.path.basename(it["image_path"]),
            "width": it["width"],
            "height": it["height"]
        })
        for ann_id, obj in enumerate(it.get("objects", []), start=len(annotations)+1):
            name = obj["label"]
            if name not in name_to_id:
                name_to_id[name] = len(name_to_id)+1
            cid = name_to_id[name]
            x,y,w,h = obj["bbox"]
            annotations.append({
                "id": ann_id,
                "image_id": img_id,
                "category_id": cid,
                "bbox": [x,y,w,h],
                "area": w*h,
                "iscrowd": 0,
                "score": obj.get("score", None)
            })
    for name, cid in name_to_id.items():
        categories.append({"id": cid, "name": name})
    return {"images": images, "annotations": annotations, "categories": categories}
PY

# --------- Main runner ----------
cat > "${PROJECT_DIR}/src/run.py" <<'PY'
import os, json, yaml, math
from typing import List, Dict, Any
from PIL import Image
from tqdm import tqdm

from taxonomy import Taxonomy
from io_utils import download_images, list_images, load_image, save_json
from exporters import to_labelstudio, to_yolo, to_coco
from llm import call_openai_vision, call_deepseek_vision
from proposals import propose_regions

def prompt_full_image():
    return """Detect AWS service icons on this architecture diagram.
Return STRICT JSON:
{
 "objects":[
   {"name":"<service-name>", "bbox":[x,y,w,h], "confidence":0.0}
 ]
}
Coordinates in pixels, integer. Only include real icons.
For service-name, use the product or service brand as seen or inferred (e.g., "Amazon S3", "AWS Lambda")."""

def prompt_patch():
    return """Identify the SINGLE most likely AWS service or product for this small icon patch.
Return STRICT JSON: {"candidates": ["<name1>", "<name2>", "<name3>"]} (max 3)."""

def choose_provider_call(provider: str, image: Image.Image, prompt: str, models: dict) -> str:
    if provider == "openai":
        return call_openai_vision(image, prompt, models["openai"]["vision_model"])
    elif provider == "deepseek":
        return call_deepseek_vision(image, prompt, models["deepseek"]["vision_model"])
    else:
        raise ValueError(f"Unknown provider: {provider}")

def safe_json(s: str) -> dict:
    import json, re
    # try direct
    try: return json.loads(s)
    except: pass
    # crude bracket extraction
    m = None
    for br in ["{", "["]:
        start = s.find(br)
        if start >= 0:
            try:
                return json.loads(s[start:])
            except:
                continue
    # last resort
    return {"objects": []}

def run_full_image(cfg, tax: Taxonomy, paths: List[str]) -> List[dict]:
    provider = cfg["provider"]
    models = cfg
    out = []
    for p in tqdm(paths, desc="Full-image LLM"):
        im = load_image(p)
        rsp = choose_provider_call(provider, im, prompt_full_image(), models)
        data = safe_json(rsp)
        W, H = im.size
        objs = []
        for o in data.get("objects", []):
            name = str(o.get("name","")).strip()
            bbox = o.get("bbox", [0,0,0,0])
            conf = float(o.get("confidence", 0.0))
            if conf < float(cfg["runtime"]["conf_threshold"]): 
                continue
            canon, score = tax.normalize(name)
            objs.append({
                "bbox": [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                "label": canon,
                "score": round(min(conf, score), 4)
            })
        out.append({"image_path": p, "width": W, "height": H, "objects": objs})
    return out

def run_patch_llm(cfg, tax: Taxonomy, paths: List[str]) -> List[dict]:
    provider = cfg["provider"]
    models = cfg
    out = []
    for p in tqdm(paths, desc="Patch-LLM"):
        im = load_image(p)
        W, H = im.size
        import cv2, numpy as np
        import numpy as _np
        img_bgr = cv2.cvtColor(_np.array(im), cv2.COLOR_RGB2BGR)
        boxes = propose_regions(img_bgr)
        objs = []
        for (x,y,w,h) in boxes:
            crop = im.crop((x,y,x+w,y+h))
            rsp = choose_provider_call(provider, crop, prompt_patch(), models)
            data = safe_json(rsp)
            cands = data.get("candidates", [])
            best_label, best_score = None, 0.0
            for cand in cands:
                canon, sc = tax.normalize(str(cand))
                if sc > best_score:
                    best_label, best_score = canon, sc
            if best_label and best_score >= 0.5:
                objs.append({"bbox":[x,y,w,h], "label": best_label, "score": round(best_score,3)})
        out.append({"image_path": p, "width": W, "height": H, "objects": objs})
    return out

def main():
    with open("config.yaml","r",encoding="utf-8") as f:
        raw = f.read()
    # allow env expansion like ${PROVIDER}
    import os
    raw = os.path.expandvars(raw)
    cfg = yaml.safe_load(raw)

    # Download if url list exists
    download_images(cfg["data"]["url_list"], cfg["data"]["images_dir"])
    paths = list_images(cfg["data"]["images_dir"])
    if not paths:
        print("No images found. Put files in ./images or fill images.txt."); return

    tax = Taxonomy.from_csv(cfg["data"]["taxonomy_csv"])

    if cfg["mode"] == "full_image_llm":
        items = run_full_image(cfg, tax, paths)
    else:
        items = run_patch_llm(cfg, tax, paths)

    os.makedirs(cfg["output"]["dir"], exist_ok=True)
    if cfg["output"]["format"] == "yolo":
        to_yolo(items, os.path.join(cfg["output"]["dir"], "yolo"))
    elif cfg["output"]["format"] == "coco":
        save_json(os.path.join(cfg["output"]["dir"], "coco.json"), to_coco(items))
    else:
        save_json(os.path.join(cfg["output"]["dir"], "labelstudio.json"), to_labelstudio(items))

    # Save raw too
    save_json(os.path.join(cfg["output"]["dir"], "raw_items.json"), items)
    print("[Done] Output saved to", cfg["output"]["dir"])

if __name__ == "__main__":
    main()
PY

# --------- Helper: tiny demo images.txt (placeholder) ----------
if [ ! -f "${URL_LIST}" ]; then
  cat > "${URL_LIST}" <<'TXT'
# 여기에 다이어그램 이미지 URL을 줄바꿈으로 추가하세요. (png/jpg)
# 예시:
# https://raw.githubusercontent.com/somewhere/sample-aws-arch.png
TXT
fi

# --------- How to run ----------
cat <<'EOM'

========================================
[사용법]
1) OpenAI 또는 DeepSeek API 키를 환경변수로 설정 (택1 또는 둘 다)
   export OPENAI_API_KEY=sk-...
   # 또는
   export DEEPSEEK_API_KEY=...

2) 이미지 준비
   - 이미지 파일을 aws_llm_autolabel/images/ 에 넣거나
   - aws_llm_autolabel/images.txt 에 URL 목록을 작성

3) 모드/출력 포맷 선택(옵션)
   export MODE=full_image_llm   # 빠른 데모 (기본)
   # 또는
   export MODE=patch_llm        # 후보영역→정규화(정확도↑)

   export OUT_FORMAT=labelstudio # 기본 (labelstudio|yolo|coco)
   export PROVIDER=openai        # 기본 (openai|deepseek)

4) 실행
   cd aws_llm_autolabel
   source .venv/bin/activate
   python src/run.py

5) 결과
   - ./out/labelstudio.json (Label Studio import)
   - ./out/yolo/*          (YOLO 라벨)
   - ./out/coco.json       (COCO)

[팁]
- full_image_llm이 월요일 시연에 가장 빠릅니다.
- 정확도 보완이 필요하면 patch_llm로 한 번 더 돌려 병합하거나,
  labelstudio.json을 Label Studio에 불러 수동 검수(반자동) 후 Export 하세요.
- taxonomy CSV의 열 이름이 다르다면 src/taxonomy.py 내 파싱 로직을 간단히 수정하세요.
========================================
EOM

