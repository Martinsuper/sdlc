import contextlib
from pathlib import Path

from sdlc.gate.models import GateDef, GateTrigger
from sdlc.utils.yaml_io import load_yaml


class GateCatalog:
    """Load gate definitions from YAML files."""

    def __init__(self) -> None:
        self.gates: dict[str, GateDef] = {}

    def load_from_yaml(self, path: Path) -> int:
        data = load_yaml(path)
        if not data or not isinstance(data, dict):
            return 0
        gate_id = data.get("id", "")
        if not gate_id:
            return 0

        # Parse after_stages into a single after_stage string (use first)
        after_stages = data.get("after_stages", [])
        after_stage = after_stages[0] if isinstance(after_stages, list) and after_stages else ""

        # Parse trigger
        trigger_str = data.get("trigger", "always")
        try:
            trigger = GateTrigger(trigger_str)
        except ValueError:
            trigger = GateTrigger.ALWAYS

        # Parse auto_pass_conditions and block_conditions from actions/auto_fail_if
        auto_pass_conditions: dict[str, object] = {}
        block_conditions: dict[str, object] = {}

        actions = data.get("actions", [])
        if isinstance(actions, list):
            auto_pass_conditions["actions"] = actions

        auto_fail_if = data.get("auto_fail_if")
        if auto_fail_if and isinstance(auto_fail_if, dict):
            block_conditions.update(auto_fail_if)

        # Parse severity_required into severities
        severities = data.get("severity_required", [])

        # Parse profiles
        profiles = data.get("profiles", [])

        gate = GateDef(
            id=gate_id,
            name=str(data.get("name", gate_id)),
            after_stage=after_stage,
            trigger=trigger,
            reviewer=data.get("reviewer_role", ""),
            deadline_hours=data.get("deadline_hours", 24),
            severities=severities if isinstance(severities, list) else [],
            profiles=profiles if isinstance(profiles, list) else [],
            auto_pass_conditions=auto_pass_conditions,
            block_conditions=block_conditions,
            approver_roles=data.get("approver_roles", []) or [],
        )
        self.gates[gate.id] = gate
        return 1

    def load_builtin(self) -> int:
        import importlib.util

        spec = importlib.util.find_spec("sdlc.builtin.gates")
        if not spec or not spec.submodule_search_locations:
            return 0
        builtin_dir = Path(spec.submodule_search_locations[0])
        count = 0
        for f in sorted(builtin_dir.glob("g*.yaml")):
            with contextlib.suppress(Exception):
                count += self.load_from_yaml(f)
        return count

    def get(self, gate_id: str) -> GateDef:
        if gate_id not in self.gates:
            raise KeyError(f"Gate not found: {gate_id}")
        return self.gates[gate_id]

    def list_gates(self) -> list[GateDef]:
        return list(self.gates.values())
