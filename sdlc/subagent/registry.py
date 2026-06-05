import contextlib
from pathlib import Path

from sdlc.subagent.models import Subagent
from sdlc.utils.exceptions import SdlcError
from sdlc.utils.yaml_io import load_yaml


class SubagentNotFoundError(SdlcError):
    pass


class SubagentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, Subagent] = {}

    def register(self, agent: Subagent) -> None:
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> Subagent:
        agent = self._agents.get(agent_id)
        if not agent:
            raise SubagentNotFoundError(f"Subagent '{agent_id}' not found in registry")
        return agent

    def list(self) -> list[Subagent]:
        return list(self._agents.values())

    def has(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def load_from_yaml(self, path: Path) -> int:
        data = load_yaml(path)
        if not data or not isinstance(data, dict):
            return 0
        agents_data = data.get("subagents", [])
        if not isinstance(agents_data, list):
            return 0
        count = 0
        for item in agents_data:
            if not isinstance(item, dict):
                continue
            agent = Subagent(
                id=item.get("id", ""),
                name=item.get("name", ""),
                role=item.get("role", ""),
                model=item.get("model", "claude-sonnet-4-20250514"),
                tools=item.get("tools", []),
                kb_inject=item.get("kb_inject", []),
                prompt=item.get("prompt", ""),
                max_iter=item.get("max_iter", 10),
                system_addon=item.get("system_addon", ""),
            )
            if agent.id:
                self.register(agent)
                count += 1
        return count

    def load_single_yaml(self, path: Path) -> int:
        """Load a single subagent definition from a YAML file (one agent per file)."""
        data = load_yaml(path)
        if not data or not isinstance(data, dict):
            return 0
        if "subagents" in data:
            # Delegate to the multi-agent format
            return self.load_from_yaml(path)
        agent = Subagent(
            id=data.get("id", ""),
            name=data.get("name", ""),
            role=data.get("role", str(data.get("name", ""))),
            model=data.get("model", "claude-sonnet-4-20250514"),
            tools=data.get("tools", []),
            kb_inject=data.get("kb_inject", []),
            prompt=data.get("prompt", ""),
            max_iter=data.get("max_iter", 10),
            system_addon=data.get("system_addon", ""),
        )
        if not agent.id:
            return 0
        self.register(agent)
        return 1

    def load_builtin(self) -> int:
        """Load all builtin subagent YAML files from sdlc/builtin/subagents/."""
        import importlib.util

        spec = importlib.util.find_spec("sdlc.builtin.subagents")
        if not spec or not spec.submodule_search_locations:
            return 0
        builtin_dir = Path(spec.submodule_search_locations[0])
        count = 0
        for f in sorted(builtin_dir.glob("sa-*.yaml")):
            with contextlib.suppress(Exception):
                count += self.load_single_yaml(f)
        return count
