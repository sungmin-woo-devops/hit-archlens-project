### References
- https://developers.hyundaimotorgroup.com/blog/570
- https://airflow.apache.org/docs/apache-airflow/stable/index.html#what-is-airflow
- https://airflow.apache.org/docs/apache-airflow/stable/index.html#workflows-as-code
- https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/plugins.html
- https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html#distributed-airflow-architecture
- https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html#separate-dag-processing-architecture
- https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/index.html
- https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html

### Airflow
Apache Airflow는 Airbnb에서 worflow들을 관리하고 스케줄링하기 위해 만든 파이썬 기반 오픈 소스입니다.
Worflow를 Python Code로 작성할 수 있으며, DAG(Directed Acyclic Graph)라는 대분류 안에 workflow들이 속하여 스케줄링됩니다.
각 worflow를 관리하기 위한 모니터링 GUI도 제공합니다.

### Airflow vs Apache Oozie
- Airflow 이전에는 Hadoop 생태계의 Oozie를 많이 사용했습니다.
- 유사한 점이 많지만, 차별적으로 가지고 있는 기능들이 많아 Airflow를 메인 스케줄러로 활용하는 경우가 증가하고 있습니다.

Airflow의 차별점
1. Open Source
2. Python 기반의 Workflow
3. Kubenetes 지원
4. 배치 플랫폼 구축이 용이함
    - Python 파일을 DAGS 경로에 두는 방식으로 모듈화된 데이터 수집 프로세스를 쉽게 구현할 수 있습니다.
    - API 관련 문서가 잘 정리되어 있기에 스케줄링, Worflow, Task 들을 API를 활용하여 관리하기 편합니다.

이 외에도 XCOM을 통한 Task 간 용이한 정보 전달
Pool을 지정하여 타이트한 스케줄 자원 관리
Sensor나 Trigger를 활용하여 이벤트에 의한 배치 flow 구성 가능

### Airflow 아키텍처
1. Basic Airflow Deployment
    - 구성: Scheduler + Webserver + Metadata DB + 내장 (Worker)
    - 특징:
        - Airflow 설치 직후 기본적으로 제공되는 형태
        - Scheduler가 Task 실행까지 직접 수행(Worker 분리 없음)
        - 개발·테스트 환경이나 소규모 워크플로우에 적합
2. Distributed Airflow Architecture
3. Seperate DAG Processing Architecture

### Airflow 아키텍처 컴포넌트 구성
#### 필수 컴포넌트 구성
- scheduler: Workflow 작업을 모두 처리하는 역할. 기본적으로 여러가지 실행 프로그램을 사용할 수 있음. 직접 작성도 가능
- webserver: 사용자가 trigger, 디버깅, DAG 실행 상태 등을 확인할 수 있는 웹 인터페이스
- DAG 파일 폴더: 스케줄러가 실행시킬 workflow 들을 읽어 들이는 경로
- metadata database: workflow와 task의 상태를 저장.

#### 선택적 컴포넌트 구성
- worker: 
    - 스케줄러에 의해 task 들을 실행시키는 역할. 
    - 기본 구성에서는 scheduler와 구분되지 않고 스케줄러가 worker의 역할도 함
    - Worker는 CeleryExecutor의 process나 KubernetesExecutor의 POd로 장기적 실행 가능
- triggrer: 
    - asyncio 이벤트 루프에서 지연된 작업을 실행
    - 지연된 작업을 사용하지 않는 기본 설치에서는 트리거가 필요하지 않음
- dag processor
    - DAG 파일을 구문 분석하고 메타데이터 데이터베이스로 직렬화
    - 기본적으로 DAG processor 프로세스는 스케줄러의 일부이지만 확장성과 보안상의 이유로 별도의 구성 요소로 실행
    - DAG Processor 있는 경우 스케줄러는 DAG 파일을 직접 읽을 필요가 없음 (DAG File Processing)

### Airflow 핵심 컨셉
Airflow는 DAG들을 관리하며, DAG마다 각각 Task들의 흐름들로 이루어져 있습니다.
Task는 각각 Operator로 구성되어 있습니다.

#### DAG (Directed Acyclic Graph | 방향성 비순환 그래프)
작업의 흐름이 다시 동작했던 작업으로 돌아오지 않고 방향성을 가지고 끝을 향해 처리하는 형태
Airflow에서 DAG는 Task들이 모여 여러 작업 흐름의 집합으로 보면 좋을 듯 함

#### Task
Task는 Airflow의 기본 실행 단위로, DAG 안에서 순서를 가지고 실행됩니다.

1. 기존 방식(Operator)
- Python 코드 상에선 변수로 선언되며, Operator 단위로 선언됩니다.
- ```python
    t2 = BashOperator(
        task_id="sleep",
        depends_on_past=False,
        bash_command="sleep 5",
        retries=3
    )
    ```

- 2.0 버전 부터 새로 나온 Taskflow는 @dag, @task와 같이 데코레이터를 활용하여
  기존의 Operator를 선언하지 않고 Task를 선언하는 방식을 소개합니다.