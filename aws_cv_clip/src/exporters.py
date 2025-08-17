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
