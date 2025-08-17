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
