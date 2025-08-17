from dotenv import load_dotenv ; load_dotenv()
from pathlib import Path
import os, json, hashlib, shutil
from typing import List, Dict, Any
from PIL import Image
import requests

PROJECT_ROOT = Path(__file__).parent.parent

def ensure_dir(p): os.makedirs(p, exist_ok=True)

def download_images(url_list_path: str, out_dir: str = PROJECT_ROOT / "images"):
    ensure_dir(out_dir)
    if not os.path.exists(url_list_path): return
    with open(url_list_path, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if not url or url.startswith('#'): continue
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
