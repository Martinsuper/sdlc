from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

RUST_AXUM_ADAPTER = AdapterDef(
    id="rust-axum",
    name="Rust Axum",
    version="1.0",
    detect_patterns=[
        {"glob": "**/Cargo.toml", "contains": "axum"},
    ],
    components=[
        ComponentDef(id="axum-router", type="web", detect="axum::Router", enforce=True),
        ComponentDef(id="tokio-runtime", type="runtime", detect="tokio::main", enforce=True),
        ComponentDef(id="sqlx", type="db", detect="sqlx::query", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["rust-must"],
    required_kb=["rules/rust-must.yaml"],
)


def register_rust_axum(registry: AdapterRegistry) -> None:
    registry.register(RUST_AXUM_ADAPTER)
