from pydantic import BaseModel


class PipelineSummary(BaseModel):
    id: str
    entry_kind: str
    profile_id: str
    status: str
    created_at: str
    updated_at: str
    stage_count: int = 0
    done_count: int = 0
    total_cost: float = 0.0


class StageResult(BaseModel):
    id: str
    pipeline_id: str
    stage_def_id: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class Artifact(BaseModel):
    id: str
    pipeline_id: str
    stage_id: str
    type: str
    path: str | None = None
    content_hash: str | None = None
    meta_json: str | None = None
    created_at: str


class KBDelta(BaseModel):
    id: int
    pipeline_id: str
    stage_id: str | None = None
    target: str
    operation: str
    fingerprint: str
    created_at: str


class ResumeState(BaseModel):
    pipeline_id: str
    token: str
    expires_at: str


class CostStat(BaseModel):
    day: str
    model: str
    calls: int
    in_tok: int
    out_tok: int
    cost: float
