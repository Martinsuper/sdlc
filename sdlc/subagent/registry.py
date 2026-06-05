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
