
import uuid

from sdlc.core.models import EntryPoint, Pipeline
from sdlc.profile.models import ProfileDef
from sdlc.stage.catalog import StageCatalog
from sdlc.stage.models import PipelineStatus, StageDef, StageNode
from sdlc.utils.time import now_utc


class PipelineBuilder:
    def __init__(self, catalog: StageCatalog) -> None:
        self.catalog = catalog

    def build(
        self,
        entry: EntryPoint,
        profile: ProfileDef,
        pipeline_id: str | None = None,
    ) -> Pipeline:
        if not pipeline_id:
            pipeline_id = f"{entry.kind.value}-{uuid.uuid4().hex[:8]}"

        stage_ids = list(profile.base_stages)
        for skip in profile.skip_stages:
            if skip in stage_ids:
                stage_ids.remove(skip)
        for extra in profile.extra_stages:
            if extra not in stage_ids:
                stage_ids.append(extra)

        # Resolve dependencies: use profile.stage_deps if defined, otherwise linear
        stage_deps = getattr(profile, "stage_deps", None) or {}
        nodes = []
        for i, sid in enumerate(stage_ids):
            try:
                stage_def = self.catalog.get(sid)
            except Exception:
                stage_def = StageDef(id=sid, name=sid, category="unknown")

            # Use explicit deps from profile if available; default to linear
            if sid in stage_deps:
                depends_on = [d for d in stage_deps[sid] if d in stage_ids]
            else:
                depends_on = [stage_ids[i - 1]] if i > 0 else []
            nodes.append(
                StageNode(
                    id=sid,
                    stage_def=stage_def,
                    depends_on=depends_on,
                    status=PipelineStatus.PENDING,
                )
            )

        now = now_utc().isoformat()
        return Pipeline(
            id=pipeline_id,
            entry=entry,
            profile=profile,
            stages=nodes,
            status=PipelineStatus.NEW,
            created_at=now,
            updated_at=now,
        )
