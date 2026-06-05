from pathlib import Path
from typing import Any

from sdlc.core.models import EntryKind, EntryPoint


class EntryDetector:
    KEYWORDS: dict[EntryKind, list[str]] = {
        EntryKind.IDEA: ["我想", "能否", "考虑", "探索"],
        EntryKind.FEATURE: ["新功能", "增加", "实现一个", "做一个", "开发"],
        EntryKind.BUG: ["报错", "异常", "不对", "失败", "bug", "错误"],
        EntryKind.HOTFIX: ["紧急", "线上", "立刻", "P0", "hotfix"],
        EntryKind.REFACTOR: ["重构", "优化", "清理", "改进"],
        EntryKind.TEST: ["测试", "覆盖率", "补单测", "单元测试"],
        EntryKind.INFRA: ["部署", "流水线", "CI", "镜像", "基础设施"],
        EntryKind.RELEASE: ["发布", "上线", "tag", "release"],
        EntryKind.REVERT: ["回滚", "revert"],
        EntryKind.DOC: ["文档", "注释", "readme", "README"],
        EntryKind.MIGRATE: ["迁移", "升级", "import 迁移"],
        EntryKind.AUDIT: ["审计", "安全", "合规", "检查"],
    }

    def detect(self, input_text: str | Path, **ctx: Any) -> EntryPoint:
        if isinstance(input_text, Path):
            input_text = str(input_text)

        best_kind = EntryKind.FEATURE
        best_score = 0.0

        for kind, keywords in self.KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in input_text.lower())
            if score > best_score:
                best_score = score
                best_kind = kind

        confidence = min(best_score / 2.0, 1.0) if best_score > 0 else 0.3

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
