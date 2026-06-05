"""Security audit tests -- verify no common security issues in production code.

These tests scan the sdlc source tree for patterns that are known security
risks:
- Hardcoded secrets (API keys, passwords, tokens)
- Use of eval/exec in production code
- SQL injection patterns (raw string interpolation in SQL)
"""

import re
from pathlib import Path

# Directories to scan
_SOURCE_ROOT = Path(__file__).resolve().parent.parent / "sdlc"

# Directories to skip
_SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".tox",
    "dist",
    "build",
}

# Patterns for hardcoded secrets
_SECRET_PATTERNS = [
    re.compile(r'(?:api[_-]?key|apikey|secret[_-]?key|password|passwd|token|auth[_-]?token)\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE),
    re.compile(r'["\'][A-Za-z0-9]{32,}["\']\s*(?:#.*secret|#.*key|#.*token)', re.IGNORECASE),
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),  # OpenAI-style API keys
    re.compile(r'sk-ant-[a-zA-Z0-9]{20,}'),  # Anthropic-style API keys
]

# Patterns for eval/exec usage
_EVAL_PATTERNS = [
    re.compile(r'\beval\s*\('),
    re.compile(r'\bexec\s*\('),
]

# Patterns for SQL injection
_SQL_INJECTION_PATTERNS = [
    # Detect SQL with f-string interpolation inside .execute() calls
    re.compile(r'\.execute\s*\(.*f["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP)\b', re.IGNORECASE),
    # Detect string concatenation in .execute() calls with SQL keywords
    re.compile(r'\.execute\s*\(\s*["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP).*["\']\s*\+', re.IGNORECASE),
    # Detect %s formatting in SQL execute calls
    re.compile(r'\.execute\s*\(.*(?:SELECT|INSERT|UPDATE|DELETE|DROP)\b.*%s', re.IGNORECASE),
]


def _collect_python_files(root: Path) -> list[Path]:
    """Collect all .py files under root, skipping _SKIP_DIRS."""
    files: list[Path] = []
    for p in root.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        files.append(p)
    return files


def _read_file(path: Path) -> str:
    """Read a Python source file safely."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


class TestNoHardcodedSecrets:
    """Verify no hardcoded secrets in source code."""

    def test_no_hardcoded_secrets(self) -> None:
        """Scan all source files for hardcoded secret patterns."""
        violations: list[str] = []
        for path in _collect_python_files(_SOURCE_ROOT):
            content = _read_file(path)
            rel = str(path.relative_to(_SOURCE_ROOT.parent))
            for i, line in enumerate(content.splitlines(), 1):
                # Skip comments
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                for pattern in _SECRET_PATTERNS:
                    if pattern.search(line):
                        # Allow known false positives: placeholder keys used in tests/deps
                        if "sk-placeholder" in line or "placeholder" in line.lower():
                            continue
                        # Allow env var lookups that happen to match patterns
                        if "os.environ" in line or "getenv" in line:
                            continue
                        # Allow test fixtures
                        if "test_" in rel:
                            continue
                        violations.append(f"{rel}:{i}: {line.strip()}")
        assert not violations, (
            "Hardcoded secrets found:\n" + "\n".join(violations)
        )


class TestNoEvalExec:
    """Verify no eval/exec usage in production code."""

    def test_no_eval_exec_in_production(self) -> None:
        """Scan production source files for eval/exec usage."""
        violations: list[str] = []
        for path in _collect_python_files(_SOURCE_ROOT):
            content = _read_file(path)
            rel = str(path.relative_to(_SOURCE_ROOT.parent))
            # Skip test files
            if "test_" in rel:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                for pattern in _EVAL_PATTERNS:
                    if pattern.search(line):
                        # Allow ast.literal_eval (it is safe)
                        if "ast.literal_eval" in line:
                            continue
                        violations.append(f"{rel}:{i}: {line.strip()}")
        assert not violations, (
            "eval/exec usage found in production code:\n" + "\n".join(violations)
        )


class TestNoSQLInjection:
    """Verify no SQL injection patterns in source code."""

    def test_no_sql_injection_patterns(self) -> None:
        """Scan source files for raw string interpolation in SQL."""
        violations: list[str] = []
        for path in _collect_python_files(_SOURCE_ROOT):
            content = _read_file(path)
            rel = str(path.relative_to(_SOURCE_ROOT.parent))
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                for pattern in _SQL_INJECTION_PATTERNS:
                    if pattern.search(line):
                        violations.append(f"{rel}:{i}: {line.strip()}")
        assert not violations, (
            "Potential SQL injection patterns found:\n" + "\n".join(violations)
        )
