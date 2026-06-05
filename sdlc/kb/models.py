"""kb — Data models for the knowledge-base engine."""

from pathlib import Path

from pydantic import BaseModel


class KBLayer(BaseModel):
    """Metadata for a single KB file (a "layer")."""

    name: str          # e.g. "architecture/component-catalog.md"
    type: str          # "markdown" | "yaml" | "json"
    path: Path         # absolute path on disk
    fingerprint: str   # sha256 hash of file content
    last_modified: str # ISO-8601 timestamp
    size_bytes: int


class KBDeltaResult(BaseModel):
    """Result of a single KB write operation."""

    target: str                  # layer name that was written
    operation: str               # "append" | "update"
    content: str                 # content that was written
    fingerprint: str             # sha256 hash of the content
    skipped: bool = False        # True when dedup prevented the write
    skip_reason: str | None = None


class ScanResult(BaseModel):
    """Result of a 7-stage KB scan (stub for M2)."""

    kb_files: dict[str, str]        # name -> content
    recommendations: list[str]
    warnings: list[str]
    confidence: float = 0.0
    next_steps: list[str] = []
