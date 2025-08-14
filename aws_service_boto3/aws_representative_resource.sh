#!/usr/bin/env bash
# aws_representative_resources.sh
# 목적: 서비스별 대표 Resource 예시 자동 추출(모델 기반 A, 가능 시 CFN 기반 B)
# 출력: out/aws_resources_models.(csv|json), out/aws_resources_cfn.(csv|json) [CFN 성공 시]

set -euo pipefail
OUTDIR="out"
PY_A="infer_from_models.py"
PY_B="extract_from_cfn.py"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install boto3 botocore >/dev/null

mkdir -p "$OUTDIR"

# ---------------- A) botocore 모델 기반: List/Describe 응답에서 식별자 추출 ----------------
cat > "$PY_A" <<'PY'
import re, csv, json, sys
import boto3, botocore.session

sess = boto3.session.Session()
bcs  = botocore.session.get_session()

service_codes = sorted(sess.get_available_services())

ID_KEYS_PRIOR = ("Arn", "Id", "Name")  # 식별자 우선순위
NEGATIVE_HINTS = ("Tag", "Policy", "Quota", "Permission", "Endpoint", "Error", "Limit", "Metadata")

def singularize(name: str) -> str:
    # 간단 단수화 휴리스틱
    if name.endswith("ies"): return name[:-3] + "y"
    if name.endswith("ses"): return name[:-2]
    if name.endswith("s") and not name.endswith("ss"): return name[:-1]
    return name

def is_negative_label(label: str) -> bool:
    return any(k.lower() in label.lower() for k in NEGATIVE_HINTS)

def score_candidate(op_name, list_name, elem_label, id_fields):
    s = 0
    # 식별자 가중치
    keys = [k for k in ID_KEYS_PRIOR if any(f.endswith(k) for f in id_fields)]
    s += 3 * len(keys)
    # 오퍼레이션 네이밍
    if op_name.lower().startswith(("list", "describe")): s += 1
    # 라벨 클린
    if is_negative_label(elem_label) or is_negative_label(list_name): s -= 3
    # 직관 이름 보너스
    if any(k.lower() in (elem_label.lower() or "") for k in ("instance","bucket","table","function","cluster","queue","topic","domain","user","role","stream","loadbalancer","dbinstance")):
        s += 1
    return s

def walk(shape, path=()):
    # 재귀적으로 list/structure 탐색 → (경로, list명, element구조, 식별필드집합) 산출
    out = []
    if shape is None: return out
    t = shape.type_name
    if t == "structure":
        for name, member in shape.members.items():
            out.extend(walk(member, path + (name,)))
    elif t == "list":
        elem = shape.member
        if elem is not None and elem.type_name == "structure":
            # 식별자로 유력한 필드 수집
            id_fields = set()
            for fname, fshape in elem.members.items():
                if fname.endswith(("Arn","Id","Name")):
                    id_fields.add(fname)
            out.append((path, path[-1] if path else "Items", elem.name or "Item", id_fields))
            # 내부도 계속 탐색(EC2 Reservations → Instances 계층 등)
            out.extend(walk(elem, path))
    return out

rows = []
for code in service_codes:
    try:
        model = bcs.get_service_model(code)
    except Exception:
        continue
    md = model.metadata or {}
    full_name = md.get("serviceFullName") or code
    ops = model.operation_names
    cand = []
    for op_name in ops:
        op = model.operation_model(op_name)
        outshape = op.output_shape
        if outshape is None: 
            continue
        for path, list_name, elem_label, id_fields in walk(outshape):
            # 후보 라벨 만들기
            label = elem_label or singularize(list_name)
            rep = singularize(label)
            sc = score_candidate(op_name, list_name, rep, id_fields)
            if sc <= 0: 
                continue
            cand.append({
                "service_code": code,
                "service_full_name": full_name,
                "operation": op_name,
                "list_name": list_name,
                "element_label": elem_label,
                "representative_resource_guess": rep,
                "id_fields": ";".join(sorted(id_fields)),
                "score": sc,
            })
    # 상위 3개만 남김
    cand.sort(key=lambda x: (-x["score"], x["representative_resource_guess"]))
    top = cand[:3] if cand else []
    rows.extend(top)

# 서비스당 1~3개 대표 리소스로 집계
# 대표 예시만 보기 좋게 첫번째 후보를 main, 나머지 secondary로 분리
agg = {}
for r in rows:
    key = (r["service_code"], r["service_full_name"])
    agg.setdefault(key, []).append(r)

final = []
for (code, name), lst in agg.items():
    lst = sorted(lst, key=lambda x: -x["score"])
    main = lst[0]
    secs = [x["representative_resource_guess"] for x in lst[1:]]
    final.append({
        "service_code": code,
        "service_full_name": name,
        "main_resource_example": main["representative_resource_guess"],
        "secondary_examples": ";".join(secs),
        "from_operation": main["operation"],
        "id_fields_seen": main["id_fields"],
    })

final.sort(key=lambda x: x["service_code"])

# 출력
import os
os.makedirs("out", exist_ok=True)
with open("out/aws_resources_models.json", "w", encoding="utf-8") as f:
    json.dump(final, f, ensure_ascii=False, indent=2)
with open("out/aws_resources_models.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(final[0].keys()))
    w.writeheader(); w.writerows(final)

print(f"OK (models): {len(final)} services → out/aws_resources_models.csv / .json", file=sys.stderr)
PY

python "$PY_A"

# ---------------- B) CloudFormation 타입 기반(가능 시) ----------------
# 자격/리전 없어 실패해도 전체 프로세스는 성공해야 하므로 '|| true'
cat > "$PY_B" <<'PY'
import boto3, csv, json, os, sys
from botocore.exceptions import BotoCoreError, ClientError

def fetch_cfn_types():
    # PUBLIC + LIVE인 AWS 네이티브 리소스 타입 수집
    cfn = boto3.client("cloudformation")
    paginator = cfn.get_paginator("list_types")
    pages = paginator.paginate(
        Visibility="PUBLIC",
        Filters={"Category": "AWS_TYPES"},
        DeprecationStatus="LIVE",
        Type="RESOURCE",
        PaginationConfig={"PageSize": 100}
    )
    types = []
    for p in pages:
        for t in p.get("TypeSummaries", []):
            n = t.get("TypeName")  # e.g., AWS::S3::Bucket
            if not n or not n.startswith("AWS::"):
                continue
            types.append(n)
    return sorted(set(types))

def to_rep_example(type_name: str) -> str:
    # "AWS::<Service>::<Resource>" → "<Resource>" 그대로
    try:
        return type_name.split("::", 2)[2]
    except Exception:
        return type_name

def main():
    try:
        types = fetch_cfn_types()
    except (BotoCoreError, ClientError) as e:
        print(f"[WARN] CFN list_types failed: {e}", file=sys.stderr)
        open("out/aws_resources_cfn.json","w").write("[]")
        open("out/aws_resources_cfn.csv","w").write("type_name,service_alias,resource\n")
        return

    rows = []
    for t in types:
        parts = t.split("::")
        if len(parts) != 3: 
            continue
        _, svc_alias, res = parts
        rows.append({
            "type_name": t,
            "service_alias": svc_alias,  # 예: S3, EC2, RDS, Lambda, Events, Logs, OpenSearchService …
            "resource": res,             # 예: Bucket, Instance, DBInstance …
        })

    # 서비스별 대표 리소스(가장 흔한 이름 우선) — 간단 집계
    from collections import defaultdict, Counter
    per_service = defaultdict(list)
    for r in rows:
        per_service[r["service_alias"]].append(r["resource"])
    agg = []
    for svc, ress in per_service.items():
        cnt = Counter(ress)
        top = [k for k,_ in cnt.most_common(3)]
        agg.append({
            "service_alias_cfn": svc,
            "main_resource_example": top[0],
            "secondary_examples": ";".join(top[1:]),
            "examples_count": len(ress),
        })
    agg.sort(key=lambda x: x["service_alias_cfn"])

    os.makedirs("out", exist_ok=True)
    with open("out/aws_resources_cfn_full.json","w",encoding="utf-8") as f: json.dump(rows,f,ensure_ascii=False,indent=2)
    with open("out/aws_resources_cfn.json","w",encoding="utf-8") as f: json.dump(agg,f,ensure_ascii=False,indent=2)
    with open("out/aws_resources_cfn.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(agg[0].keys()))
        w.writeheader(); w.writerows(agg)
    print(f"OK (cfn): {len(agg)} services → out/aws_resources_cfn.csv / .json", file=sys.stderr)

if __name__=="__main__":
    main()
PY

# 실행(B). 실패해도 계속.
python "$PY_B" || true

echo "결과:"
ls -1 "$OUTDIR"/*.csv "$OUTDIR"/*.json 2>/dev/null || true
