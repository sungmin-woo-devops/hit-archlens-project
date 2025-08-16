#!/usr/bin/env python3
"""
infer_from_models.py
목적: botocore 서비스 모델을 기반으로 각 AWS 서비스의 대표 Resource 예시를 자동 추출
- 순환 참조 안전(BFS) 탐색으로 RecursionError 방지
- 'List/Describe' 응답 구조에서 Arn/Id/Name 필드 탐지로 대표 리소스 추정
출력: out/aws_resources_models.csv, out/aws_resources_models.json
"""

from collections import deque
import csv
import json
import os
import re
import sys

import boto3
import botocore.session


# 세션/메타는 함수 내부에서 생성하여 재사용성 향상

# ---- 설정/휴리스틱 ----
MAX_DEPTH = 8
ID_KEYS_PRIOR = ("Arn", "Id", "Name")  # 식별자 우선순위
NEGATIVE_HINTS = ("Tag", "Policy", "Quota", "Permission", "Endpoint", "Error", "Limit", "Metadata")

def singularize(name: str) -> str:
    # 간단 단수화 휴리스틱
    if not name:
        return name
    if name.endswith("ies"): return name[:-3] + "y"
    if name.endswith("ses"): return name[:-2]
    if name.endswith("s") and not name.endswith("ss"): return name[:-1]
    return name

def normalize_resource_label(label: str) -> str:
    if not label:
        return "Item"
    l = singularize(label)
    # TableNames -> Table, FunctionArns -> Function 등 휴리스틱
    for suf in ("Names", "Name", "Arns", "Arn", "Ids", "Id"):
        if l.endswith(suf):
            l = l[: -len(suf)]
            break
    return l or "Item"

def is_negative_label(label: str) -> bool:
    s = (label or "").lower()
    return any(k.lower() in s for k in NEGATIVE_HINTS)

def score_candidate(op_name, list_name, elem_label, id_fields):
    s = 0
    keys = [k for k in ID_KEYS_PRIOR if any(f.endswith(k) for f in id_fields)]
    s += 3 * len(keys)
    if (op_name or "").lower().startswith(("list", "describe")):
        s += 1
    if is_negative_label(elem_label) or is_negative_label(list_name):
        s -= 3
    if any(k in (elem_label or "").lower() for k in (
        "instance","bucket","table","function","cluster","queue","topic",
        "domain","user","role","stream","loadbalancer","dbinstance"
    )):
        s += 1
    return s

def safe_get_member(shape):
    try:
        return shape.member
    except RecursionError:
        return None
    except Exception:
        return None

def iter_walk_output_shape(output_shape):
    """
    순환 안전한 BFS:
      - structure: 멤버로 확장
      - list of structure: 대표 리소스 후보 산출 + element 구조로 확장
      - list of scalar: 리스트명으로 대표 리소스 후보 산출
      - map/기타: 무시
    산출: (path, list_name, elem_label, id_fields_set)
    """
    if output_shape is None:
        return

    seen = set()  # shape 객체 id 단위로 방문 제어
    q = deque()
    q.append( ((), output_shape, 0) )  # (경로, shape, depth)

    while q:
        path, shape, depth = q.popleft()
        if shape is None:
            continue
        sid = id(shape)
        if sid in seen:
            continue
        seen.add(sid)
        if depth > MAX_DEPTH:
            continue

        t = shape.type_name
        if t == "structure":
            # ResponseMetadata/토큰류는 패스
            for name, member in (shape.members or {}).items():
                if name in ("ResponseMetadata", "NextToken", "Marker", "NextMarker", "ContinuationToken"):
                    continue
                q.append( (path + (name,), member, depth + 1) )

        elif t == "list":
            elem = safe_get_member(shape)
            list_name = path[-1] if path else "Items"
            if elem is None:
                continue
            if elem.type_name == "structure":
                # 구조체 원소 → 식별자 필드 수집
                id_fields = set(fname for fname, fshape in (elem.members or {}).items()
                                if fname.endswith(ID_KEYS_PRIOR))
                elem_label = elem.name or "Item"
                yield (path, list_name, elem_label, id_fields)
                # 중첩(예: Reservations -> Instances) 탐색
                q.append( (path, elem, depth + 1) )
            else:
                # 스칼라 리스트(예: TableNames: [string])도 대표 리소스로 취급
                rep = normalize_resource_label(list_name)
                yield (path, list_name, rep, set([rep + "Name"]))

        # map/기타 타입은 리소스 후보로 쓰지 않음

def infer_from_models(
    out_csv: str = "out/aws_resources_models.csv",
    out_json: str = "out/aws_resources_models.json",
) -> None:
    """Infer representative resources for AWS services using botocore models."""

    sess = boto3.session.Session()
    bcs = botocore.session.get_session()
    service_codes = sorted(sess.get_available_services())

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
            try:
                op = model.operation_model(op_name)
                outshape = op.output_shape
            except Exception:
                continue
            if outshape is None:
                continue
            for path, list_name, elem_label, id_fields in iter_walk_output_shape(outshape):
                # 후보 라벨 만들기
                label = normalize_resource_label(elem_label or list_name)
                sc = score_candidate(op_name, list_name, label, id_fields)
                if sc <= 0:
                    continue
                cand.append(
                    {
                        "service_code": code,
                        "service_full_name": full_name,
                        "operation": op_name,
                        "list_name": list_name,
                        "element_label": elem_label,
                        "representative_resource_guess": label,
                        "id_fields": ";".join(sorted(id_fields)),
                        "score": sc,
                    }
                )
        # 상위 3개만 남김
        cand.sort(key=lambda x: (-x["score"], x["representative_resource_guess"]))
        top = cand[:3] if cand else []
        rows.extend(top)

    # 서비스당 1~3개 대표 리소스로 집계
    agg: dict[tuple[str, str], list[dict[str, str]]] = {}
    for r in rows:
        key = (r["service_code"], r["service_full_name"])
        agg.setdefault(key, []).append(r)

    final = []
    for (code, name), lst in agg.items():
        lst = sorted(lst, key=lambda x: -x["score"])
        main = lst[0]
        secs = [x["representative_resource_guess"] for x in lst[1:]]
        final.append(
            {
                "service_code": code,
                "service_full_name": name,
                "main_resource_example": main["representative_resource_guess"],
                "secondary_examples": ";".join(secs),
                "from_operation": main["operation"],
                "id_fields_seen": main["id_fields"],
            }
        )

    final.sort(key=lambda x: x["service_code"])

    # ---- 출력 ----
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    fieldnames = [
        "service_code",
        "service_full_name",
        "main_resource_example",
        "secondary_examples",
        "from_operation",
        "id_fields_seen",
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in final:
            w.writerow(r)

    print(
        f"OK (models): {len(final)} services → {out_csv} / {out_json}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    infer_from_models()
