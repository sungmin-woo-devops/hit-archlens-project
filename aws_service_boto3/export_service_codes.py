"""Export metadata for all services exposed by boto3."""

from __future__ import annotations

import csv
import json

import boto3
import botocore.session


def export_service_codes(
    out_csv: str = "aws_service_codes.csv",
    out_json: str = "aws_service_codes.json",
) -> None:
    """Dump service metadata to CSV and JSON files.

    Parameters
    ----------
    out_csv:
        Where to write the CSV output.
    out_json:
        Where to write the JSON output.
    """

    sess = boto3.session.Session()
    bcs = botocore.session.get_session()

    service_codes = sorted(sess.get_available_services())
    resource_codes = set(sess.get_available_resources())

    rows: list[dict[str, object]] = []
    for code in service_codes:
        model = bcs.get_service_model(code)  # 네트워크 호출 없음
        md = model.metadata or {}
        full_name = md.get("serviceFullName") or code
        endpoint_prefix = md.get("endpointPrefix") or code
        api_version = md.get("apiVersion")
        uid = md.get("uid")
        # protocols: 일부는 list, 일부는 단일 값
        protos = md.get("protocols") or md.get("protocol")
        if isinstance(protos, list):
            protos = ",".join(sorted(protos))

        regions = sorted(sess.get_available_regions(code))  # 기본 partition=aws
        has_resources = code in resource_codes
        is_global = len(regions) == 0

        rows.append(
            {
                "service_code": code,
                "service_full_name": full_name,
                "endpoint_prefix": endpoint_prefix,
                "api_version": api_version,
                "protocols": protos,
                "uid": uid,
                "regions": ";".join(regions),
                "region_count": len(regions),
                "is_global_like": is_global,
                "has_resource_interface": has_resources,
            }
        )

    # 출력
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {out_csv} / {out_json}")


if __name__ == "__main__":
    export_service_codes()
