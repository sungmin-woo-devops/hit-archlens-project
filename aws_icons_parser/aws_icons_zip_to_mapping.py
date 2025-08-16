#!/usr/bin/env python3
"""Parse the official AWS icon ZIP and produce mapping files.

The original version of this script executed immediately on import and relied on
``sys.argv`` for configuration.  For easier reuse (for example from an Airflow
task) the core logic is now exposed via :func:`generate_mapping` and the CLI
behaviour is preserved under ``if __name__ == "__main__"``.

Example
-------
``python aws_icons_zip_to_mapping.py Asset-Package.zip``
"""

from __future__ import annotations

import csv
import json
import pathlib
import re
import sys
import zipfile
from collections import defaultdict

SUFFIX = re.compile(r"(_?(Dark|Light))?(_?\d{2})?(\.svg|\.png)$", re.I)

# ZIP 구조 상 고정된 루트
RES_ROOT_HINT = "Resource-Icons_"
RES_DIR_PREFIX = "Res_"
SERVICE_FILE_PREFIX = "Res_"

# 그룹 표준화(공식 명칭과 폴더명 차이 보정)
GROUP_NORMALIZE = {
    "Networking Content Delivery": "Networking & Content Delivery",
    "Security Identity Compliance": "Security, Identity, & Compliance",
    "Management Governance": "Management & Governance",
    "Application Integration": "Application Integration",
    "Developer Tools": "Developer Tools",
    "Front End Web Mobile": "Front-End Web & Mobile",
    "End User Computing": "End User Computing",
    "Machine Learning": "Machine Learning",
    "Quantum Technologies": "Quantum Technologies",
    "Migration Modernization": "Migration & Modernization",
    # 필요 시 추가
}

def norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def norm_group(folder_name: str) -> str | None:
    # "Res_Security-Identity-Compliance" -> "Security, Identity, & Compliance"
    name = folder_name
    if name.startswith(RES_DIR_PREFIX):
        name = name[len(RES_DIR_PREFIX):]
    name = name.replace("-", " ")
    name = norm_spaces(name)
    return GROUP_NORMALIZE.get(name, name)

def norm_service_from_file(stem: str) -> str:
    # "Res_Amazon-OpenSearch-Service_Data-Node_48" -> "Amazon OpenSearch Service"
    s = stem
    if s.startswith(SERVICE_FILE_PREFIX):
        s = s[len(SERVICE_FILE_PREFIX):]
    # 서비스 기본명은 첫 '_' 이전
    base = s.split("_", 1)[0]
    base = base.replace("-", " ")
    base = norm_spaces(base)
    return base

def is_icon_file(p: str) -> bool:
    p = p.lower()
    return (p.endswith(".svg") or p.endswith(".png"))

def generate_mapping(
    zip_path: str = "Asset-Package.zip",
    out_csv: str = "aws_icons_mapping.csv",
    out_json: str = "aws_icons_mapping.json",
) -> None:
    """Generate mapping files from an AWS icon ZIP archive.

    Parameters
    ----------
    zip_path:
        Path to the AWS icon package ZIP.
    out_csv:
        Path to write the CSV mapping file.
    out_json:
        Path to write the JSON mapping file.
    """

    rows = []
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        for f in names:
            if not is_icon_file(f):
                continue
            parts = pathlib.PurePosixPath(f).parts
            if not any(RES_ROOT_HINT in p for p in parts):
                continue  # 리소스 아이콘만 사용
            if len(parts) < 3:
                continue
            group_folder = parts[-2]        # e.g., "Res_Security-Identity-Compliance"
            service_file = parts[-1]        # e.g., "Res_Amazon-EC2_Instance_48.svg"

            group = norm_group(group_folder)
            stem = SUFFIX.sub("", service_file)  # 사이즈/테마/확장자 제거
            stem = stem.rsplit(".", 1)[0] if "." in stem else stem

            service = norm_service_from_file(stem)

            # 잡음/유틸 제거
            if len(service) < 2 or service.lower() in {"learn more", "pricing", "faq"}:
                continue

            rows.append((group, None, service, f))

    # 중복 제거
    seen, out = set(), []
    for g, c, s, p in rows:
        key = (g or "", c or "", s or "")
        if key in seen:
            continue
        seen.add(key)
        out.append((g, c, s, p))

    # 저장
    with open(out_csv, "w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(["group", "category", "service", "zip_path"])
        w.writerows(out)

    with open(out_json, "w", encoding="utf-8") as fp:
        json.dump(
            [{"group": g, "category": c, "service": s, "zip_path": p} for g, c, s, p in out],
            fp,
            ensure_ascii=False,
            indent=2,
        )

    print(f"[OK] CSV: {out_csv}  rows={len(out)}")
    print(f"[OK] JSON:{out_json}  rows={len(out)}")


if __name__ == "__main__":
    zip_arg = sys.argv[1] if len(sys.argv) > 1 else "Asset-Package.zip"
    csv_arg = sys.argv[2] if len(sys.argv) > 2 else "aws_icons_mapping.csv"
    json_arg = sys.argv[3] if len(sys.argv) > 3 else "aws_icons_mapping.json"
    generate_mapping(zip_arg, csv_arg, json_arg)
