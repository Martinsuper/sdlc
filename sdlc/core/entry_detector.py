import re
from pathlib import Path
from typing import Any

from sdlc.core.models import EntryKind, EntryPoint


class EntryDetector:
    KEYWORDS: dict[EntryKind, list[str]] = {
        EntryKind.IDEA: ["我想", "能否", "考虑", "探索", "idea", "brainstorm", "wish", "imagine", "concept", "proposal"],
        EntryKind.FEATURE: ["新功能", "增加", "实现一个", "做一个", "开发", "feature", "new", "add", "implement", "request", "enhancement"],
        EntryKind.BUG: ["报错", "异常", "不对", "失败", "bug", "错误", "fix", "defect", "issue", "error", "fault", "crash"],
        EntryKind.HOTFIX: ["紧急", "线上", "立刻", "P0", "hotfix", "urgent", "critical", "emergency", "outage", "patch", "asap"],
        EntryKind.REFACTOR: ["重构", "优化", "清理", "改进", "refactor", "restructure", "cleanup", "optimize", "simplify", "reorganize"],
        EntryKind.TEST: ["测试", "覆盖率", "补单测", "单元测试", "test", "coverage", "unittest", "spec", "verify", "qa"],
        EntryKind.INFRA: ["部署", "流水线", "CI", "镜像", "基础设施", "deploy", "pipeline", "ci", "infrastructure", "container", "devops"],
        EntryKind.RELEASE: ["发布", "上线", "tag", "release", "publish", "launch", "ship", "rollout", "version", "deploy-to-prod"],
        EntryKind.REVERT: ["回滚", "revert", "rollback", "undo", "backout", "restore", "downgrade"],
        EntryKind.DOC: ["文档", "注释", "readme", "README", "documentation", "comment", "guide", "tutorial", "docs", "help"],
        EntryKind.MIGRATE: ["迁移", "升级", "import 迁移", "migrate", "upgrade", "transition", "port", "move", "convert", "migration"],
        EntryKind.AUDIT: ["审计", "安全", "合规", "检查", "audit", "security", "compliance", "review", "inspect", "assessment", "scan"],
    }

    @staticmethod
    def _is_cjk_char(ch: str) -> bool:
        """Check if a character is CJK (Chinese/Japanese/Korean)."""
        cp = ord(ch)
        return (
            (0x4E00 <= cp <= 0x9FFF)
            or (0x3400 <= cp <= 0x4DBF)
            or (0xF900 <= cp <= 0xFAFF)
            or (0x2F800 <= cp <= 0x2FA1F)
        )

    @staticmethod
    def _keyword_matches(keyword: str, text: str) -> bool:
        """Match keyword against text. Use word-boundary matching for English,
        substring matching for CJK keywords (which lack space-based word boundaries)."""
        is_cjk = any(EntryDetector._is_cjk_char(ch) for ch in keyword)
        if is_cjk:
            return keyword.lower() in text.lower()
        # English keyword: use word boundary matching
        pattern = r'\b' + re.escape(keyword) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def detect(self, input_text: str | Path, **ctx: Any) -> EntryPoint:
        if isinstance(input_text, Path):
            input_text = str(input_text)

        best_kind = EntryKind.FEATURE
        best_score = 0.0

        for kind, keywords in self.KEYWORDS.items():
            score = sum(1 for kw in keywords if self._keyword_matches(kw, input_text))
            if score > best_score:
                best_score = score
                best_kind = kind

        confidence = min(best_score / 2.0, 1.0) if best_score > 0 else 0.1

        attachments = []
        if isinstance(input_text, str):
            for word in input_text.split():
                if word.startswith("@") or word.startswith("/") or word.startswith("./"):
                    attachments.append(word)

        return EntryPoint(
            kind=best_kind,
            raw_input=input_text,
            detected_attachments=attachments,
            confidence=confidence,
        )
