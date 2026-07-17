"""Format an sdlc JSON run result as a PR comment and post it via gh (M-C3).

Reads the machine-readable output of `sdlc run --format json` and turns it into
a compact Markdown comment, then posts it with the gh CLI. Kept dependency-free
(stdlib only) so it runs in a bare CI step.
"""

from __future__ import annotations

import json
import subprocess
import sys


def format_comment(result: dict) -> str:
    status = result.get("status", "unknown")
    emoji = {"completed": "✅", "failed": "❌", "waiting_approval": "⏸️"}.get(status, "ℹ️")
    lines = [f"### {emoji} sdlc review: `{status}`", ""]
    if result.get("error"):
        lines.append(f"**Error:** {result['error']}")
        lines.append("")
    stages = result.get("stages", [])
    if stages:
        lines.append("| stage | status | error |")
        lines.append("|---|---|---|")
        for s in stages:
            lines.append(f"| {s.get('id', '?')} | {s.get('status', '?')} | {s.get('error') or ''} |")
    cost = result.get("cost_usd")
    if cost is not None:
        lines.append("")
        lines.append(f"_cost: ${cost:.4f}_")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: comment.py <result.json>", file=sys.stderr)
        return 2
    try:
        result = json.loads(open(argv[0], encoding="utf-8").read())
    except (OSError, json.JSONDecodeError) as e:
        print(f"cannot read result: {e}", file=sys.stderr)
        return 1
    body = format_comment(result)
    # Post via gh; if unavailable (e.g. local run), just print the body.
    try:
        subprocess.run(["gh", "pr", "comment", "--body", body], check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
