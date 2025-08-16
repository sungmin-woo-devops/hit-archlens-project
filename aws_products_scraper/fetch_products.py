#!/usr/bin/env python3
"""Fetch the public AWS products feed and store as JSON/CSV.

This avoids the dependency on Scrapy and keeps the scraper lightweight for use in
Airflow or simple scripts.  The endpoint is unauthenticated and returns metadata
about all AWS products.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

import requests

API_URL = (
    "https://aws.amazon.com/api/dirs/items/search?"
    "item.directoryId=aws-products&"
    "sort_by=item.additionalFields.productNameLowercase&size=1000&"
    "language=en&item.locale=en_US"
)


def fetch_products(out_json: str = "aws_products.json", out_csv: str = "aws_services.csv") -> None:
    """Fetch product metadata and persist to files."""
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # JSON dump
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    rows: Iterable[list[str]] = []
    for item in data.get("items", []):
        af = item.get("item", {}).get("additionalFields", {})
        rows.append(
            [
                af.get("productCategory", ""),
                af.get("productName", ""),
                af.get("productUrl", ""),
            ]
        )

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["group", "service", "service_url"])
        w.writerows(rows)

    print(f"Wrote {out_json} and {out_csv}")


if __name__ == "__main__":
    fetch_products()
