from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

DATA_SPARK_ADAPTER = AdapterDef(
    id="data-spark",
    name="Apache Spark",
    version="1.0",
    detect_patterns=[
        {"glob": "**/pom.xml", "contains": "spark-core"},
        {"glob": "**/requirements.txt", "contains": "pyspark"},
    ],
    components=[
        ComponentDef(id="spark-sql", type="sql", detect="SparkSession", enforce=True),
        ComponentDef(id="spark-streaming", type="streaming", detect="StreamingContext", enforce=True),
        ComponentDef(id="spark-ml", type="ml", detect="Pipeline", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["data-must"],
    required_kb=["rules/data-must.yaml"],
)


def register_data_spark(registry: AdapterRegistry) -> None:
    registry.register(DATA_SPARK_ADAPTER)
