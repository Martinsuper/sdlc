import pytest

from sdlc.llm.models import ContentBlock, Role
from sdlc.subagent.builtin import BUILTIN_SUBAGENTS, register_builtins
from sdlc.subagent.models import Subagent, SubagentResult, SubagentTask
from sdlc.subagent.pool import SubagentPool
from sdlc.subagent.registry import SubagentNotFoundError, SubagentRegistry


class TestSubagent:
    def test_create_defaults(self):
        a = Subagent(id="SA-0", name="test", role="test", model="m")
        assert a.id == "SA-0"
        assert a.tools == []
        assert a.kb_inject == []
        assert a.prompt == ""
        assert a.max_iter == 10
        assert a.system_addon == ""

    def test_create_full(self):
        a = Subagent(
            id="SA-1",
            name="demo",
            role="r",
            model="m",
            tools=["read"],
            kb_inject=["x.md"],
            prompt="hi",
            max_iter=5,
            system_addon="extra",
        )
        assert a.tools == ["read"]
        assert a.kb_inject == ["x.md"]
        assert a.prompt == "hi"
        assert a.max_iter == 5
        assert a.system_addon == "extra"


class TestSubagentTask:
    def test_create_defaults(self):
        t = SubagentTask(agent_id="SA-1", input="do stuff")
        assert t.agent_id == "SA-1"
        assert t.input == "do stuff"
        assert t.context == {}
        assert t.artifacts_required == []
        assert t.pipeline_id == ""
        assert t.stage_id == ""
        assert t.max_iter is None

    def test_create_full(self):
        t = SubagentTask(
            agent_id="SA-1",
            input="go",
            context={"k": 1},
            artifacts_required=["doc"],
            pipeline_id="P-1",
            stage_id="S-1",
            max_iter=3,
        )
        assert t.context == {"k": 1}
        assert t.max_iter == 3


class TestSubagentResult:
    def test_success(self):
        r = SubagentResult(success=True, output="done")
        assert r.success is True
        assert r.output == "done"
        assert r.artifacts == {}
        assert r.tool_calls == []
        assert r.iterations == 0
        assert r.cost_usd == 0.0
        assert r.error is None

    def test_failure(self):
        r = SubagentResult(success=False, error="boom")
        assert r.success is False
        assert r.error == "boom"


class TestSubagentRegistry:
    def _make_agent(self, id="SA-1"):
        return Subagent(id=id, name="a", role="r", model="m")

    def test_register_and_get(self):
        reg = SubagentRegistry()
        agent = self._make_agent()
        reg.register(agent)
        assert reg.get("SA-1") is agent

    def test_get_not_found(self):
        reg = SubagentRegistry()
        with pytest.raises(SubagentNotFoundError, match="not found"):
            reg.get("SA-999")

    def test_list(self):
        reg = SubagentRegistry()
        reg.register(self._make_agent("SA-1"))
        reg.register(self._make_agent("SA-2"))
        assert len(reg.list()) == 2

    def test_has(self):
        reg = SubagentRegistry()
        reg.register(self._make_agent())
        assert reg.has("SA-1") is True
        assert reg.has("SA-2") is False

    def test_load_from_yaml(self, tmp_dir):
        yaml_content = {
            "subagents": [
                {"id": "SA-1", "name": "a1", "role": "r1", "model": "m1", "tools": ["read"]},
                {"id": "SA-2", "name": "a2", "role": "r2", "model": "m2"},
            ]
        }
        p = tmp_dir / "agents.yaml"
        from sdlc.utils.yaml_io import save_yaml

        save_yaml(p, yaml_content)
        reg = SubagentRegistry()
        count = reg.load_from_yaml(p)
        assert count == 2
        assert reg.has("SA-1")
        assert reg.get("SA-1").tools == ["read"]

    def test_load_from_yaml_empty(self, tmp_dir):
        p = tmp_dir / "empty.yaml"
        from sdlc.utils.yaml_io import save_yaml

        save_yaml(p, {})
        reg = SubagentRegistry()
        assert reg.load_from_yaml(p) == 0

    def test_load_from_yaml_skips_empty_id(self, tmp_dir):
        yaml_content = {"subagents": [{"id": "", "name": "bad"}]}
        p = tmp_dir / "agents.yaml"
        from sdlc.utils.yaml_io import save_yaml

        save_yaml(p, yaml_content)
        reg = SubagentRegistry()
        assert reg.load_from_yaml(p) == 0


class TestRegisterBuiltins:
    def test_registers_all(self):
        reg = SubagentRegistry()
        count = register_builtins(reg)
        # Hardcoded 11 + YAML overrides (same IDs, so same agent count)
        assert count >= 11
        assert len(reg.list()) == 11

    def test_builtin_ids(self):
        reg = SubagentRegistry()
        register_builtins(reg)
        for i in range(1, 12):
            assert reg.has(f"SA-{i}")

    def test_builtin_data(self):
        assert len(BUILTIN_SUBAGENTS) == 11
        for item in BUILTIN_SUBAGENTS:
            assert "id" in item
            assert "name" in item
            assert "role" in item


class TestSubagentPool:
    def _make_pool(self):
        reg = SubagentRegistry()
        register_builtins(reg)
        pool = SubagentPool(registry=reg, llm=None, audit=None)
        return pool, reg

    def test_build_initial_messages_with_prompt_and_input(self):
        pool, _reg = self._make_pool()
        agent = Subagent(id="X", name="x", role="r", model="m", prompt="system prompt")
        task = SubagentTask(agent_id="X", input="user request")
        msgs = pool._build_initial_messages(agent, task)
        assert len(msgs) == 1
        assert msgs[0].role == Role.USER
        assert "system prompt" in msgs[0].content
        assert "user request" in msgs[0].content

    def test_build_initial_messages_with_context(self):
        pool, _ = self._make_pool()
        agent = Subagent(id="X", name="x", role="r", model="m")
        task = SubagentTask(agent_id="X", input="go", context={"key": "val"})
        msgs = pool._build_initial_messages(agent, task)
        assert "Context:" in msgs[0].content

    def test_extract_text(self):
        pool, _ = self._make_pool()
        blocks = [
            ContentBlock(type="text", text="hello"),
            ContentBlock(type="tool_use", name="read", id="1"),
            ContentBlock(type="text", text="world"),
        ]
        result = pool._extract_text(blocks)
        assert result == "hello\nworld"

    def test_extract_text_empty(self):
        pool, _ = self._make_pool()
        assert pool._extract_text([]) == ""

    def test_parse_artifacts_dict(self):
        pool, _ = self._make_pool()
        text = '```json\n{"foo": "bar"}\n```'
        result = pool._parse_artifacts(text)
        assert result == {"foo": "bar"}

    def test_parse_artifacts_list(self):
        pool, _ = self._make_pool()
        text = "```json\n[1, 2, 3]\n```"
        result = pool._parse_artifacts(text)
        assert result == {"block_0": [1, 2, 3]}

    def test_parse_artifacts_multiple(self):
        pool, _ = self._make_pool()
        text = '```json\n{"a": 1}\n```\nblah\n```json\n{"b": 2}\n```'
        result = pool._parse_artifacts(text)
        assert result == {"a": 1, "b": 2}

    def test_parse_artifacts_invalid_json(self):
        pool, _ = self._make_pool()
        text = "```json\nnot json\n```"
        result = pool._parse_artifacts(text)
        assert result == {}

    def test_parse_artifacts_no_blocks(self):
        pool, _ = self._make_pool()
        assert pool._parse_artifacts("plain text") == {}
