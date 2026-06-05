
from sdlc.core.models import EntryPoint, Pipeline
from sdlc.profile.models import ProfileDef
from sdlc.stage.catalog import StageCatalog
from sdlc.stage.models import StageDef, StageNode
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
            pipeline_id = f"{entry.kind.value}-{now_utc().strftime('%Y-%m-%d-%H%M%S')}"

        stage_ids = list(profile.base_stages)
        for skip in profile.skip_stages:
            if skip in stage_ids:
                stage_ids.remove(skip)
        for extra in profile.extra_stages:
            if extra not in stage_ids:
                stage_ids.append(extra)

        nodes = []
        for i, sid in enumerate(stage_ids):
            try:
                stage_def = self.catalog.get(sid)
            except Exception:
                stage_def = StageDef(id=sid, name=sid, category="unknown")

            depends_on = [stage_ids[i - 1]] if i > 0 else []
            nodes.append(
                StageNode(
                    id=sid,
                    stage_def=stage_def,
                    depends_on=depends_on,
                    status="PENDING",
                )
            )

        now = now_utc().isoformat()
        return Pipeline(
            id=pipeline_id,
            entry=entry,
            profile=profile,
            stages=nodes,
            status="NEW",
            created_at=now,
            updated_at=now,
        )
