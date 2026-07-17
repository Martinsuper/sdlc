"""LLM-as-judge (M-D2).

Scores a produced artifact against a case's acceptance criteria (and optional
Rule-library MUSTs) across four dimensions. Uses a configurable, typically
stronger, judge model — a stronger judge over a weaker producer is the seed of
the reflect/judge shared-criteria idea from M-A2.

The judge is intentionally decoupled from any live provider in tests: pass a
client whose ``complete`` returns a canned score, and no network/API key is
needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sdlc.eval.models import EvalCase, Score
from sdlc.subagent.runtime import _extract_json

if TYPE_CHECKING:
    from sdlc.llm.client import MultiLLMClient

_DIMENSIONS = ("correctness", "completeness", "rule_compliance", "kb_alignment")


def _clamp01(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))


class Judge:
    def __init__(self, llm: MultiLLMClient, judge_model: str = "") -> None:
        self.llm = llm
        self.judge_model = judge_model

    def _prompt(self, case: EvalCase, produced: str, criteria: list[str], rules: list[dict[str, Any]]) -> str:
        crit_block = "\n".join(f"- {c}" for c in criteria) or "(none provided)"
        rule_block = (
            "\n".join(f"- [{r.get('level', '?')}] {r.get('description', r)}" for r in rules)
            or "(none)"
        )
        return (
            "You are an impartial evaluator of an AI-produced software artifact. "
            "Score it 0..1 on each dimension and return ONLY JSON of the form "
            '{"correctness": float, "completeness": float, "rule_compliance": '
            'float, "kb_alignment": float, "overall": float, "rationale": string}.\n\n'
            f"Task input:\n{case.input}\n\n"
            f"Acceptance criteria:\n{crit_block}\n\n"
            f"MUST rules:\n{rule_block}\n\n"
            f"Produced artifact:\n{produced[:8000]}"
        )

    async def score(
        self,
        case: EvalCase,
        produced: str,
        criteria: list[str] | None = None,
        rules: list[dict[str, Any]] | None = None,
    ) -> Score:
        from sdlc.llm.models import CompletionRequest, Message, Role

        criteria = criteria if criteria is not None else case.criteria
        rules = rules or []
        req = CompletionRequest(
            model=self.judge_model or "",
            messages=[Message(role=Role.USER, content=self._prompt(case, produced, criteria, rules))],
            metadata={"phase": "judge", "case_id": case.id},
        )
        resp = await self.llm.complete(req)
        text = "\n".join(b.text for b in resp.content if b.type == "text" and b.text)
        data = _extract_json(text)
        if not isinstance(data, dict):
            # Unparseable judgment scores zero rather than silently passing —
            # a judge that can't answer must not certify quality.
            return Score(rationale="judge returned unparseable output")

        dims = {d: _clamp01(data.get(d, 0.0)) for d in _DIMENSIONS}
        overall = data.get("overall")
        overall_f = _clamp01(overall) if overall is not None else sum(dims.values()) / len(dims)
        return Score(
            correctness=dims["correctness"],
            completeness=dims["completeness"],
            rule_compliance=dims["rule_compliance"],
            kb_alignment=dims["kb_alignment"],
            overall=overall_f,
            rationale=str(data.get("rationale", "")),
        )
