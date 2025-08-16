# 사전설치: pip install apache-airflow[celery,postgres,redis]
from airflow import DAG
from airflow.models import Variable
from airflow.decorators import task
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta

default_args = dict(retries=2, retry_delay=timedelta(minutes=2))

with DAG(
    dag_id="rss_ingest_fast",
    start_date=datetime(2025, 8, 1),
    schedule="*/15 * * * *",
    catchup=False,
    default_args=default_args,
    max_active_runs=1,
    tags=["rss","news","ai"],
) as dag:

    FEEDS = Variable.get("RSS_FEEDS_FAST", deserialize_json=True)  # ["https://...", ...]

    @task.pool("web_fetch_pool")
    def fetch(url: str) -> dict:
        # 요청/파싱(요약), 원문 링크/발행시각 추출
        # 반환: {"url":..., "items":[{title,link,pub,summary,source}]}
        ...

    @task
    def normalize(batch: dict) -> list[dict]:
        # 스키마 정규화, 해시 생성
        ...

    @task
    def sink(rows: list[dict]):
        # S3/Kafka/DB 적재 + upsert(idempotent)
        ...

    with TaskGroup("per_feed") as per_feed:
        results = fetch.expand(url=FEEDS)
        sink.expand(rows=normalize.expand(batch=results))