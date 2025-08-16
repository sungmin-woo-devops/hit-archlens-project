"""Airflow DAG to run AWS data gathering tasks in sequence."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.decorators import task

# Ensure project root on path so our local packages are importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aws_icons_parser.aws_icons_zip_to_mapping import generate_mapping
from aws_products_scraper.fetch_products import fetch_products
from aws_service_boto3.export_service_codes import export_service_codes
from aws_service_boto3.infer_from_models import infer_from_models


default_args = {"retries": 1}

with DAG(
    dag_id="aws_data_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    default_args=default_args,
    tags=["aws", "batch"],
) as dag:

    @task()
    def parse_icons():
        generate_mapping()

    @task()
    def scrape_products():
        fetch_products()

    @task()
    def export_codes():
        export_service_codes()

    @task()
    def infer_resources():
        infer_from_models()

    parse_icons() >> scrape_products() >> export_codes() >> infer_resources()
