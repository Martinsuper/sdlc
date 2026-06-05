from datetime import datetime, timedelta
from typing import Any

from sdlc.audit.events import AuditEventType
from sdlc.audit.logger import AuditLogger
from sdlc.gate.models import GateAction, GateDecision, GateDef
from sdlc.gate.triggers import should_trigger


class GateEngine:
    def __init__(self, audit: AuditLogger | None = None) -> None:
        self.audit = audit
        self._gates: list[GateDef] = []

    def register(self, gate_def: GateDef) -> None:
        self._gates.append(gate_def)

    def register_all(self, gates: list[GateDef]) -> None:
        for g in gates:
            self.register(g)

    def list_gates(self) -> list[GateDef]:
        return list(self._gates)

    def evaluate(self, stage_id: str, context: dict[str, Any]) -> GateDecision | None:
        applicable = [g for g in self._gates if g.after_stage == stage_id]
        if not applicable:
            return None

        last_decision = None
        for gate_def in applicable:
            if not should_trigger(gate_def, context):
                continue

            decision = self._evaluate_one(gate_def, context)

            if self.audit:
                self.audit.emit(
                    AuditEventType.GATE_TRIGGERED,
                    {
                        "gate_id": gate_def.id,
                        "after_stage": stage_id,
                        "action": decision.action.value,
                        "reason": decision.reason,
                    },
                    pipeline_id=context.get("pipeline_id"),
                )

            if decision.action == GateAction.AUTO_PASS:
                last_decision = decision
                continue

            return decision

        return last_decision

    def _evaluate_one(self, gate_def: GateDef, context: dict[str, Any]) -> GateDecision:
        if self._check_auto_pass(gate_def, context):
            return GateDecision(
                gate_id=gate_def.id,
                action=GateAction.AUTO_PASS,
                reason="Auto-pass conditions met",
            )

        if self._check_block(gate_def, context):
            # Check for rule exceptions before blocking
            rule_id = context.get("rule_id", "")
            if rule_id and self._has_active_exception(rule_id, context):
                return GateDecision(
                    gate_id=gate_def.id,
                    action=GateAction.AUTO_PASS,
                    reason=f"Rule {rule_id} has active exception",
                )
            return GateDecision(
                gate_id=gate_def.id,
                action=GateAction.BLOCK,
                reason=self._block_reason(gate_def, context),
            )

        deadline = ""
        if gate_def.deadline_hours:
            deadline = (
                datetime.utcnow() + timedelta(hours=gate_def.deadline_hours)
            ).isoformat() + "Z"

        return GateDecision(
            gate_id=gate_def.id,
            action=GateAction.MANUAL_REVIEW,
            reason=f"Gate {gate_def.id} requires manual review",
            reviewer=gate_def.reviewer,
            deadline=deadline,
        )

    def _has_active_exception(self, rule_id: str, context: dict[str, Any]) -> bool:
        """Check if a rule has an active exception in the ExceptionManager."""
        try:
            from sdlc.rule.exceptions import ExceptionManager
            from sdlc.utils.paths import project_root

            kb_root = project_root() / "doc" / "kb"
            if not kb_root.exists():
                return False
            exc_mgr = ExceptionManager(kb_root)
            result = exc_mgr.is_active(rule_id, context)
            return result is not None
        except Exception:
            return False

    def _check_auto_pass(self, gate_def: GateDef, context: dict[str, Any]) -> bool:
        conditions = gate_def.auto_pass_conditions
        if not conditions:
            return False
        if conditions.get("no_violations") and context.get("rule_violations"):
            return False
        return not (conditions.get("no_failures") and context.get("stage_status") == "FAILED")

    def _check_block(self, gate_def: GateDef, context: dict[str, Any]) -> bool:
        conditions = gate_def.block_conditions
        if not conditions:
            return False
        if conditions.get("on_must_violation"):
            violations = context.get("rule_violations", [])
            if any(v.get("level") == "MUST" for v in violations):
                return True
        return bool(conditions.get("on_failure") and context.get("stage_status") == "FAILED")

    def _block_reason(self, gate_def: GateDef, context: dict[str, Any]) -> str:
        conditions = gate_def.block_conditions
        if conditions.get("on_must_violation"):
            violations = context.get("rule_violations", [])
            must_violations = [v for v in violations if v.get("level") == "MUST"]
            if must_violations:
                return f"Blocked by MUST rule violations: {[v.get('id') for v in must_violations]}"
        if conditions.get("on_failure"):
            return "Blocked due to stage failure"
        return f"Blocked by gate {gate_def.id}"
