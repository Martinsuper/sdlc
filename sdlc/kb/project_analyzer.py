"""Source code content collector for LLM analysis.

Intelligently collects source code snippets from a project for LLM-based
analysis, controlling total size and prioritizing the most valuable files.
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path

# Directories to always skip
SKIP_DIRS: frozenset[str] = frozenset({
    ".git", ".svn", ".hg", "__pycache__", "node_modules", "vendor",
    ".venv", "venv", "env", ".tox", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "dist", "build", "egg-info", ".eggs", ".next",
    ".nuxt", "target", "bin", "obj", "out", ".gradle", ".idea",
    ".vscode", ".sdlc", "doc", "docs",
})

# Binary / non-source extensions to skip
SKIP_EXTENSIONS: frozenset[str] = frozenset({
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".class", ".jar", ".war", ".ear", ".png", ".jpg", ".jpeg",
    ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot",
    ".mp3", ".mp4", ".avi", ".mov", ".zip", ".tar", ".gz",
    ".bz2", ".7z", ".rar", ".db", ".sqlite", ".lock",
    ".min.js", ".min.css",
})

# Source file extensions by language
SOURCE_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py", ".pyi"],
    "java": [".java"],
    "kotlin": [".kt", ".kts"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx", ".mts", ".cts"],
    "go": [".go"],
    "rust": [".rs"],
    "swift": [".swift"],
    "dart": [".dart"],
    "hcl": [".tf", ".tfvars"],
    "yaml": [".yaml", ".yml"],
    "toml": [".toml"],
    "sql": [".sql"],
    "proto": [".proto"],
    "graphql": [".graphql", ".gql"],
    "xml": [".xml"],
}

# Glob patterns for different source categories
CATEGORY_PATTERNS: dict[str, list[str]] = {
    "model": [
        "**/model/**", "**/models/**", "**/entity/**", "**/entities/**",
        "**/domain/**", "**/schema/**", "**/schemas/**", "**/dto/**",
        "**/po/**", "**/vo/**", "**/bo/**", "**/do/**",
    ],
    "api": [
        "**/controller/**", "**/controllers/**", "**/router/**", "**/routers/**",
        "**/api/**", "**/handler/**", "**/handlers/**", "**/resource/**",
        "**/resources/**", "**/endpoint/**", "**/endpoints/**",
        "**/action/**", "**/actions/**",
    ],
    "service": [
        "**/service/**", "**/services/**", "**/logic/**", "**/core/**",
        "**/business/**", "**/manager/**", "**/managers/**",
        "**/processor/**", "**/processors/**", "**/engine/**",
    ],
    "config": [
        "**/config/**", "**/configuration/**", "**/settings/**",
        "**/conf/**",
    ],
}

# Priority ordering: higher priority files are collected first
FILE_PRIORITY_PATTERNS: list[tuple[str, int]] = [
    # Entry points - highest priority
    ("**/main.{py,go,rs,java,kt,ts,js}", 100),
    ("**/app.{py,ts,js}", 95),
    ("**/Application.java", 95),
    # Config files
    ("**/pyproject.toml", 90),
    ("**/pom.xml", 90),
    ("**/build.gradle*", 90),
    ("**/package.json", 90),
    ("**/go.mod", 90),
    ("**/Cargo.toml", 90),
    ("**/settings.py", 85),
    ("**/application.{yml,yaml,properties}", 85),
    # API/Controller
    ("**/controller/**", 70),
    ("**/router/**", 70),
    ("**/api/**", 70),
    # Model/Entity
    ("**/model/**", 60),
    ("**/entity/**", 60),
    ("**/domain/**", 60),
    # Service
    ("**/service/**", 50),
    ("**/logic/**", 50),
]


def _expand_glob_pattern(pattern: str) -> list[str]:
    """Expand brace patterns like ``main.{py,go,rs}`` into separate patterns.

    Only handles the common ``{a,b,c}`` syntax used in FILE_PRIORITY_PATTERNS.
    Returns a list with a single element if no braces are present.
    """
    m = re.search(r"\{([^}]+)\}", pattern)
    if not m:
        return [pattern]
    alternatives = m.group(1).split(",")
    return [pattern[: m.start()] + alt + pattern[m.end() :] for alt in alternatives]


# Pre-expand FILE_PRIORITY_PATTERNS so brace groups are resolved at import time.
_EXPANDED_PRIORITY_PATTERNS: list[tuple[str, int]] = []
for _pat, _pri in FILE_PRIORITY_PATTERNS:
    for _expanded in _expand_glob_pattern(_pat):
        _EXPANDED_PRIORITY_PATTERNS.append((_expanded, _pri))


class ProjectAnalyzer:
    """Collects source code snippets from a project for LLM analysis.

    Intelligently selects and truncates source files to fit within a
    token budget, prioritizing the most valuable files.
    """

    def __init__(
        self,
        root: Path,
        max_files: int = 50,
        max_lines_per_file: int = 200,
        max_total_chars: int = 32000,
    ) -> None:
        self.root = root
        self.max_files = max_files
        self.max_lines_per_file = max_lines_per_file
        self.max_total_chars = max_total_chars

    def collect_file_tree(self, max_depth: int = 4) -> str:
        """Generate a human-readable file tree string."""
        lines: list[str] = []
        self._walk_tree(self.root, prefix="", depth=0, max_depth=max_depth, lines=lines)
        return "\n".join(lines)

    def collect_source_snippets(
        self,
        patterns: list[str] | None = None,
        language: str | None = None,
    ) -> str:
        """Collect source code snippets, controlling total size.

        Args:
            patterns: Optional glob patterns to filter files. If None, collects all source files.
            language: Optional language filter (e.g. "python", "java").

        Returns:
            Concatenated source snippets with file path headers.
        """
        files = self._discover_files(patterns=patterns, language=language)
        files = self._rank_files(files)
        return self._build_snippets(files)

    def collect_model_sources(self) -> str:
        """Collect model/entity/domain related source files."""
        return self.collect_source_snippets(patterns=CATEGORY_PATTERNS["model"])

    def collect_api_sources(self) -> str:
        """Collect controller/router/api/handler related source files."""
        return self.collect_source_snippets(patterns=CATEGORY_PATTERNS["api"])

    def collect_service_sources(self) -> str:
        """Collect service/logic/core related source files."""
        return self.collect_source_snippets(patterns=CATEGORY_PATTERNS["service"])

    def collect_config_sources(self) -> str:
        """Collect configuration file content."""
        return self.collect_source_snippets(patterns=CATEGORY_PATTERNS["config"])

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _walk_tree(
        self,
        directory: Path,
        prefix: str,
        depth: int,
        max_depth: int,
        lines: list[str],
    ) -> None:
        """Recursively walk directory and build a tree string."""
        if depth > max_depth:
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            return

        # Skip hidden and excluded directories
        entries = [
            e for e in entries
            if e.name not in SKIP_DIRS and not e.name.startswith(".")
        ]

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                self._walk_tree(entry, prefix + extension, depth + 1, max_depth, lines)

    def _discover_files(
        self,
        patterns: list[str] | None = None,
        language: str | None = None,
    ) -> list[Path]:
        """Discover source files matching criteria."""
        files: list[Path] = []

        if patterns:
            # Use glob patterns
            seen: set[Path] = set()
            for pattern in patterns:
                for match in self.root.glob(pattern):
                    if match.is_file() and self._should_include(match, language):
                        abs_path = match.resolve()
                        if abs_path not in seen:
                            seen.add(abs_path)
                            files.append(abs_path)
        else:
            # Walk the tree
            for dirpath, dirnames, filenames in os.walk(self.root):
                # Filter out skip directories in-place
                dirnames[:] = [
                    d for d in dirnames
                    if d not in SKIP_DIRS and not d.startswith(".")
                ]
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    if self._should_include(filepath, language):
                        files.append(filepath.resolve())

        return files

    def _should_include(self, filepath: Path, language: str | None = None) -> bool:
        """Check if a file should be included in analysis."""
        # Skip binary extensions
        if filepath.suffix.lower() in SKIP_EXTENSIONS:
            return False

        # Skip very large files (>1MB)
        try:
            if filepath.stat().st_size > 1_000_000:
                return False
        except OSError:
            return False

        # Check if it's a source file
        ext = filepath.suffix.lower()
        is_source = any(ext in exts for exts in SOURCE_EXTENSIONS.values())

        if not is_source:
            # Also include common config files (exact names)
            config_names = {
                "dockerfile", "docker-compose.yml", "docker-compose.yaml",
                "makefile", "cmakelists.txt", "jenkinsfile",
                ".gitlab-ci.yml",
            }
            # Also include config files matched by glob patterns
            config_globs = [
                ".github/workflows/*.yml",
                ".github/workflows/*.yaml",
            ]
            rel_lower = str(filepath.relative_to(self.root)).replace("\\", "/").lower()
            if filepath.name.lower() not in config_names and \
               not any(fnmatch.fnmatch(rel_lower, g) for g in config_globs):
                return False

        # Language filter
        if language:
            lang_exts = SOURCE_EXTENSIONS.get(language, [])
            if lang_exts and ext not in lang_exts:
                return False

        return True

    def _rank_files(self, files: list[Path]) -> list[Path]:
        """Rank files by priority (higher priority first)."""
        scored: list[tuple[Path, int]] = []

        for filepath in files:
            score = 0
            rel_path_str = str(filepath.relative_to(self.root)).replace("\\", "/")

            for pattern, priority in _EXPANDED_PRIORITY_PATTERNS:
                # Use fnmatch for glob-style pattern matching.
                # Strip leading "**/" to allow matching from any depth.
                match_pattern = pattern.lstrip("*").lstrip("/")
                if fnmatch.fnmatch(rel_path_str, match_pattern) or \
                   fnmatch.fnmatch(rel_path_str, pattern):
                    score = max(score, priority)

            # Default score for unmatched files
            if score == 0:
                # Prefer shorter paths (closer to root)
                depth = rel_path_str.count("/")
                score = max(1, 30 - depth * 5)

            scored.append((filepath, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [f for f, _ in scored]

    def _build_snippets(self, files: list[Path]) -> str:
        """Build concatenated snippets from ranked files, respecting size limits."""
        snippets: list[str] = []
        total_chars = 0
        count = 0

        for filepath in files:
            if count >= self.max_files:
                break
            if total_chars >= self.max_total_chars:
                break

            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue

            # Truncate to max lines
            lines = content.splitlines(keepends=True)
            if len(lines) > self.max_lines_per_file:
                lines = lines[: self.max_lines_per_file]
                lines.append(f"... (truncated, {len(content.splitlines())} total lines)\n")
                content = "".join(lines)

            rel_path = filepath.relative_to(self.root)
            header = f"### File: {rel_path}\n"
            snippet = f"{header}```\n{content}```\n\n"

            # Check if adding this snippet would exceed the limit
            if total_chars + len(snippet) > self.max_total_chars:
                # Try to fit a truncated version
                remaining = self.max_total_chars - total_chars - len(header) - 10
                if remaining > 200:
                    snippet = f"{header}```\n{content[:remaining]}\n... (truncated)\n```\n\n"
                    snippets.append(snippet)
                    total_chars += len(snippet)
                    count += 1
                break

            snippets.append(snippet)
            total_chars += len(snippet)
            count += 1

        if not snippets:
            return "(No source files found for analysis)"

        return f"## Source Code Snippets ({count} files)\n\n" + "".join(snippets)
