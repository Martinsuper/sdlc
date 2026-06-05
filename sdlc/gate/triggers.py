from typing import Any

from sdlc.gate.models import GateDef, GateTrigger


def should_trigger(gate_def: GateDef, context: dict[str, Any]) -> bool:
    trigger = gate_def.trigger

    if trigger == GateTrigger.ALWAYS:
        return True

    if trigger == GateTrigger.ON_SEVERITY:
        severity = context.get("severity")
        if severity and gate_def.severities:
            return severity in gate_def.severities
        return False

    if trigger == GateTrigger.ON_ARTIFACT:
        artifact_types = context.get("artifact_types", [])
        target_types = gate_def.auto_pass_conditions.get("artifact_types", [])
        if target_types:
            return any(at in target_types for at in artifact_types)
        return bool(artifact_types)

    if trigger == GateTrigger.ON_RULE_VIOLATION:
        violations = context.get("rule_violations", [])
        min_severity = gate_def.auto_pass_conditions.get("min_violation_level", "MUST")
        return any(v.get("level") == min_severity for v in violations)

    if trigger == GateTrigger.ON_FAILURE:
        stage_status: str = context.get("stage_status", "")
        return stage_status == "FAILED"

    if trigger == GateTrigger.ON_STAGE_END:
        stage_id: str = context.get("stage_id", "")
        return stage_id == gate_def.after_stage

    return False
