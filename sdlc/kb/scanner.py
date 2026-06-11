"""kb -- 7-stage project scanner with parallel file reading and result caching."""

import asyncio
import hashlib
import json
import logging
import os
import re
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from sdlc.kb.models import ScanResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Manifest file names to look for
# ---------------------------------------------------------------------------
MANIFESTS = {
    "package.json",
    "pom.xml",
    "go.mod",
    "Cargo.toml",
    "pyproject.toml",
    "build.gradle",
    "requirements.txt",
}

# CI config paths (relative to project root)
CI_PATHS: list[str] = [
    ".github/workflows",
    ".gitlab-ci.yml",
    ".circleci",
    "Jenkinsfile",
]

# Container config paths
CONTAINER_PATHS: list[str] = [
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "k8s",
]

# Known entry point file names
ENTRY_POINTS: list[str] = [
    "main.py",
    "app.py",
    "manage.py",
    "main.go",
    "Application.java",
    "index.ts",
    "index.js",
    "index.tsx",
    "index.jsx",
    "main.rs",
]

# Extension -> language mapping
EXT_LANG: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C",
    ".hpp": "C++",
    ".scala": "Scala",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".sh": "Shell",
    ".bash": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
}

# Lint config files
LINT_CONFIGS: list[str] = [
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.json",
    ".eslintrc.yml",
    ".eslintrc.yaml",
    ".pylintrc",
    "checkstyle.xml",
    "ruff.toml",
    ".ruff.toml",
    ".rubocop.yml",
    "pyrightconfig.json",
    "tslint.json",
    "golangci.yml",
    "golangci.yaml",
    ".swiftlint.yml",
]

# Formatter config files
FORMATTER_CONFIGS: list[str] = [
    ".prettierrc",
    ".prettierrc.js",
    ".prettierrc.json",
    ".prettierrc.yml",
    ".prettierrc.yaml",
    ".editorconfig",
    "rustfmt.toml",
    ".rustfmt.toml",
]

# Git hook paths
GIT_HOOK_PATHS: list[str] = [
    ".husky",
    ".git/hooks/pre-commit",
    ".pre-commit-config.yaml",
]

# Pre-compiled regex patterns for manifest parsers (performance)
_RE_PYPROJECT_NAME = re.compile(r'name\s*=\s*"([^"]+)"')
_RE_PYPROJECT_DEP = re.compile(r'\s*"([^"<>=!~\s]+)')
_RE_POM_GROUP = re.compile(r"<groupId>([^<]+)</groupId>")
_RE_POM_ARTIFACT = re.compile(r"<artifactId>([^<]+)</artifactId>")
_RE_POM_DEP = re.compile(r"<dependency>.*?<artifactId>([^<]+)</artifactId>", re.DOTALL)
_RE_GO_MODULE = re.compile(r"^module\s+(\S+)", re.MULTILINE)
_RE_GO_REQUIRE = re.compile(r"\s*(\S+)")
_RE_CARGO_NAME = re.compile(r'name\s*=\s*"([^"]+)"')
_RE_CARGO_DEP = re.compile(r"([a-zA-Z0-9_-]+)\s*=")
_RE_REQ_DEP = re.compile(r"([a-zA-Z0-9._-]+)")

# Maximum parallel readers for file I/O
_MAX_PARALLEL_READERS = 8

# Maximum files to include in file tree walk (prevents memory issues on huge repos)
_MAX_WALK_FILES = 50_000


# ---------------------------------------------------------------------------
# ScanContext -- internal data holder
# ---------------------------------------------------------------------------


class ScanContext:
    """Mutable data holder that accumulates scan results across stages."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.file_tree: list[str] = []
        self.manifests: dict[str, dict[str, Any]] = {}
        self.ci_configs: list[str] = []
        self.container_configs: list[str] = []
        self.languages: dict[str, int] = {}
        self.frameworks: list[str] = []
        self.build_tools: list[str] = []
        self.dependencies: dict[str, list[str]] = {}
        self.entry_points: list[str] = []
        self.key_modules: list[str] = []
        self.lint_configs: list[str] = []
        self.formatter_configs: list[str] = []
        self.git_hooks: list[str] = []
        self.existing_docs: list[str] = []
        self.existing_adrs: list[str] = []
        self.existing_changelogs: list[str] = []
        self.existing_kb: bool = False
        self.ai_summary: str | None = None


# ---------------------------------------------------------------------------
# Manifest parsers
# ---------------------------------------------------------------------------


def _read_file_safe(path: Path) -> str | None:
    """Read a file and return its text content, or None on failure."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _parse_package_json(path: Path) -> dict[str, Any]:
    """Parse package.json and extract name, dependencies, devDependencies, scripts."""
    text = _read_file_safe(path)
    if text is None:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    result: dict[str, Any] = {"name": data.get("name", "")}
    deps = data.get("dependencies", {})
    dev_deps = data.get("devDependencies", {})
    result["dependencies"] = list(deps.keys())
    result["devDependencies"] = list(dev_deps.keys())
    result["scripts"] = list(data.get("scripts", {}).keys())
    return result


def _parse_pyproject_toml(path: Path) -> dict[str, Any]:
    """Basic text parsing of pyproject.toml (no external toml lib needed)."""
    text = _read_file_safe(path)
    if text is None:
        return {}
    result: dict[str, Any] = {"name": "", "dependencies": []}
    m = _RE_PYPROJECT_NAME.search(text)
    if m:
        result["name"] = m.group(1)
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "dependencies = [":
            in_deps = True
            continue
        if in_deps:
            if stripped.startswith("]"):
                in_deps = False
                continue
            dep_match = _RE_PYPROJECT_DEP.match(stripped)
            if dep_match:
                result["dependencies"].append(dep_match.group(1))
    return result


def _parse_pom_xml(path: Path) -> dict[str, Any]:
    """Basic regex parsing of pom.xml."""
    text = _read_file_safe(path)
    if text is None:
        return {}
    result: dict[str, Any] = {"groupId": "", "artifactId": "", "dependencies": []}
    m = _RE_POM_GROUP.search(text)
    if m:
        result["groupId"] = m.group(1)
    m = _RE_POM_ARTIFACT.search(text)
    if m:
        result["artifactId"] = m.group(1)
    dep_ids = _RE_POM_DEP.findall(text)
    result["dependencies"] = dep_ids
    return result


def _parse_go_mod(path: Path) -> dict[str, Any]:
    """Parse go.mod for module name and requires."""
    text = _read_file_safe(path)
    if text is None:
        return {}
    result: dict[str, Any] = {"module": "", "requires": []}
    m = _RE_GO_MODULE.search(text)
    if m:
        result["module"] = m.group(1)
    in_require = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require:
            if stripped == ")":
                in_require = False
                continue
            req_match = _RE_GO_REQUIRE.match(stripped)
            if req_match:
                result["requires"].append(req_match.group(1))
        elif stripped.startswith("require "):
            parts = stripped.split()
            if len(parts) >= 2:
                result["requires"].append(parts[1])
    return result


def _parse_cargo_toml(path: Path) -> dict[str, Any]:
    """Basic text parsing of Cargo.toml."""
    text = _read_file_safe(path)
    if text is None:
        return {}
    result: dict[str, Any] = {"name": "", "dependencies": []}
    m = _RE_CARGO_NAME.search(text)
    if m:
        result["name"] = m.group(1)
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "[dependencies]":
            in_deps = True
            continue
        if in_deps:
            if stripped.startswith("["):
                in_deps = False
                continue
            dep_match = _RE_CARGO_DEP.match(stripped)
            if dep_match:
                result["dependencies"].append(dep_match.group(1))
    return result


def _parse_requirements_txt(path: Path) -> dict[str, Any]:
    """Parse requirements.txt for dependency names."""
    text = _read_file_safe(path)
    if text is None:
        return {}
    deps: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = _RE_REQ_DEP.match(line)
        if m:
            deps.append(m.group(1))
    return {"dependencies": deps}


# Map manifest filenames to their parsers
_MANIFEST_PARSERS: dict[str, Any] = {
    "package.json": _parse_package_json,
    "pyproject.toml": _parse_pyproject_toml,
    "pom.xml": _parse_pom_xml,
    "go.mod": _parse_go_mod,
    "Cargo.toml": _parse_cargo_toml,
    "requirements.txt": _parse_requirements_txt,
}


# ---------------------------------------------------------------------------
# Framework detection helpers
# ---------------------------------------------------------------------------


def _detect_frameworks_from_manifests(manifests: dict[str, dict[str, Any]]) -> list[str]:
    """Detect frameworks from parsed manifest data."""
    frameworks: list[str] = []

    pkg = manifests.get("package.json", {})
    all_deps = set(pkg.get("dependencies", []) + pkg.get("devDependencies", []))
    if "react" in all_deps:
        frameworks.append("react")
    if "vue" in all_deps:
        frameworks.append("vue")
    if "angular" in all_deps or "@angular/core" in all_deps:
        frameworks.append("angular")
    if "next" in all_deps:
        frameworks.append("next.js")
    if "nuxt" in all_deps:
        frameworks.append("nuxt")
    if "express" in all_deps:
        frameworks.append("express")
    if "fastify" in all_deps:
        frameworks.append("fastify")
    if "nestjs" in all_deps or "@nestjs/core" in all_deps:
        frameworks.append("nestjs")
    if "svelte" in all_deps:
        frameworks.append("svelte")

    pom = manifests.get("pom.xml", {})
    pom_deps = set(pom.get("dependencies", []))
    if "spring-boot-starter" in pom_deps or any(
        "spring-boot" in d for d in pom_deps
    ):
        frameworks.append("spring-boot")
    if "dong-boot" in pom_deps or any(
        "dongboot" in d or "dong-boot" in d for d in pom_deps
    ):
        frameworks.append("dongboot")

    pyproj = manifests.get("pyproject.toml", {})
    reqs = manifests.get("requirements.txt", {})
    py_deps = set(pyproj.get("dependencies", []) + reqs.get("dependencies", []))
    if "flask" in py_deps:
        frameworks.append("flask")
    if "django" in py_deps:
        frameworks.append("django")
    if "fastapi" in py_deps:
        frameworks.append("fastapi")
    if "celery" in py_deps:
        frameworks.append("celery")
    if "sqlalchemy" in py_deps:
        frameworks.append("sqlalchemy")

    gomod = manifests.get("go.mod", {})
    go_deps = set(gomod.get("requires", []))
    for d in go_deps:
        if "gin-gonic" in d:
            frameworks.append("gin")
        elif "echo" in d:
            frameworks.append("echo")
        elif "fiber" in d:
            frameworks.append("fiber")

    cargo = manifests.get("Cargo.toml", {})
    cargo_deps = set(cargo.get("dependencies", []))
    if "actix" in cargo_deps or "actix-web" in cargo_deps:
        frameworks.append("actix-web")
    if "axum" in cargo_deps:
        frameworks.append("axum")
    if "tokio" in cargo_deps:
        frameworks.append("tokio")
    if "rocket" in cargo_deps:
        frameworks.append("rocket")

    return frameworks


def _detect_build_tools(manifests: dict[str, dict[str, Any]], languages: dict[str, int]) -> list[str]:
    """Detect build tools from manifests and languages."""
    tools: list[str] = []
    if "pom.xml" in manifests:
        tools.append("maven")
    if "build.gradle" in manifests:
        tools.append("gradle")
    if "package.json" in manifests:
        tools.append("npm")
    if "pyproject.toml" in manifests or "requirements.txt" in manifests:
        tools.append("pip")
    if "go.mod" in manifests:
        tools.append("go")
    if "Cargo.toml" in manifests:
        tools.append("cargo")
    if not tools:
        if "Java" in languages:
            tools.append("maven")
        if "Python" in languages:
            tools.append("pip")
        if "Go" in languages:
            tools.append("go")
        if "Rust" in languages:
            tools.append("cargo")
        if "JavaScript" in languages or "TypeScript" in languages:
            tools.append("npm")
    return tools


# ---------------------------------------------------------------------------
# Scan result cache
# ---------------------------------------------------------------------------


class ScanResultCache:
    """File-content-based cache to skip re-reading unchanged files across scans.

    The fingerprint is captured at ``put()`` time from the file's bytes.
    ``get()`` compares the stored fingerprint with the current file bytes
    without re-reading the content for parsing -- if the fingerprint matches,
    the previously parsed result is reused.
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[str, dict[str, Any]]] = {}  # path -> (fingerprint, parsed)

    def get(self, path: Path) -> dict[str, Any] | None:
        """Return cached parse result if the file content hasn't changed."""
        key = str(path)
        cached = self._cache.get(key)
        if cached is None:
            return None
        stored_fp, parsed = cached
        # Compare fingerprint from disk without reading full content.
        try:
            current_fp = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return None
        if current_fp == stored_fp:
            return parsed
        return None

    def put(self, path: Path, parsed: dict[str, Any]) -> None:
        """Store a parse result keyed by file content fingerprint."""
        try:
            fp = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return
        self._cache[str(path)] = (fp, parsed)

    def clear(self) -> None:
        self._cache.clear()


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class Scanner:
    """Seven-stage project scanner for ``sdlc init``."""

    def __init__(self, root: Path, config: dict[str, Any] | None = None) -> None:
        self.root = root
        self.config = config or {}
        self._result_cache = ScanResultCache()

    def scan(self, depth: int = 5, no_llm: bool = False) -> ScanResult:
        """Run the 7-stage scan pipeline."""
        context = ScanContext(root=self.root)
        self._stage1_basic(context, depth)
        self._stage2_techstack(context)
        self._stage3_components(context)
        self._stage4_standards(context)
        self._stage5_import_existing(context)
        if not no_llm:
            self._stage6_ai_analysis(context)
        return self._stage7_generate_result(context)

    def _stage1_basic(self, ctx: ScanContext, depth: int) -> None:
        """File tree, manifests, CI, containers -- with parallel manifest reading."""
        ctx.file_tree = self._walk_file_tree(ctx.root, depth)

        # Collect manifest paths that exist
        manifest_paths: list[tuple[str, Path]] = []
        for name in MANIFESTS:
            p = ctx.root / name
            if p.is_file():
                manifest_paths.append((name, p))

        # Parse manifests in parallel using ThreadPoolExecutor
        if manifest_paths:
            with ThreadPoolExecutor(max_workers=min(len(manifest_paths), _MAX_PARALLEL_READERS)) as pool:
                futures = {}
                for name, path in manifest_paths:
                    parser = _MANIFEST_PARSERS.get(name)
                    if parser is not None:
                        # Check cache first
                        cached = self._result_cache.get(path)
                        if cached is not None:
                            ctx.manifests[name] = cached
                        else:
                            futures[pool.submit(parser, path)] = (name, path)
                    else:
                        ctx.manifests[name] = {}

            for future in as_completed(futures):
                name, path = futures[future]
                try:
                    parsed = future.result()
                    ctx.manifests[name] = parsed
                    self._result_cache.put(path, parsed)
                except Exception:
                    logger.warning("Manifest %s parse failed", name)
                    ctx.manifests[name] = {}

        for ci_path in CI_PATHS:
            p = ctx.root / ci_path
            if p.exists():
                ctx.ci_configs.append(ci_path)
        for cont_path in CONTAINER_PATHS:
            p = ctx.root / cont_path
            if p.exists():
                ctx.container_configs.append(cont_path)

    def _walk_file_tree(self, root: Path, depth: int) -> list[str]:
        """Walk the file tree up to *depth* levels, returning relative paths.

        *depth* semantics: top-level files have depth=0, files inside a
        top-level sub-directory have depth=1, etc.  Walking stops once
        ``current_depth >= depth``.

        The number of files is capped at ``_MAX_WALK_FILES`` to avoid
        excessive memory consinternal-monitoringtion on very large repositories.
        """
        result: list[str] = []
        base_str = str(root)
        base_len = len(base_str)
        for dirpath, dirnames, filenames in os.walk(str(root)):
            # Compute depth relative to root.
            # rel_dir is empty for root itself (depth 0).
            # Each "/" in rel_dir adds one level of depth.
            rel_dir = dirpath[base_len:].lstrip("/").lstrip("\\")
            # depth 0 = root, depth 1 = top-level sub-directory, etc.
            current_depth = rel_dir.count("/") if rel_dir else 0
            if current_depth >= depth:
                dirnames.clear()
                continue
            dirnames[:] = [
                d
                for d in dirnames
                if not d.startswith(".")
                and d not in (
                    "node_modules",
                    "__pycache__",
                    ".git",
                    "venv",
                    ".venv",
                    "dist",
                    "build",
                    "target",
                    ".tox",
                )
            ]
            for fname in sorted(filenames):
                if fname.startswith("."):
                    continue
                full = Path(dirpath) / fname
                try:
                    rel = str(full.relative_to(root))
                except ValueError:
                    continue
                result.append(rel)
                if len(result) >= _MAX_WALK_FILES:
                    logger.warning(
                        "File tree walk capped at %d files; remaining files skipped",
                        _MAX_WALK_FILES,
                    )
                    return sorted(result)
        return sorted(result)

    def _stage2_techstack(self, ctx: ScanContext) -> None:
        """Language, framework, and build tool detection."""
        for rel_path in ctx.file_tree:
            ext = Path(rel_path).suffix.lower()
            lang = EXT_LANG.get(ext)
            if lang:
                ctx.languages[lang] = ctx.languages.get(lang, 0) + 1
        ctx.frameworks = _detect_frameworks_from_manifests(ctx.manifests)
        ctx.build_tools = _detect_build_tools(ctx.manifests, ctx.languages)

    def _stage3_components(self, ctx: ScanContext) -> None:
        """Dependencies, entry points, key modules."""
        for name, parsed in ctx.manifests.items():
            deps: list[str] = []
            if isinstance(parsed, dict):
                deps = list(parsed.get("dependencies", []))
                dev_deps = parsed.get("devDependencies", [])
                if dev_deps:
                    deps = deps + dev_deps
            if deps:
                ctx.dependencies[name] = deps
        for ep in ENTRY_POINTS:
            for candidate in [ctx.root / ep, ctx.root / "src" / ep, ctx.root / "cmd" / ep]:
                if candidate.is_file():
                    ctx.entry_points.append(str(candidate.relative_to(ctx.root)))
        for d in ctx.root.iterdir():
            if d.is_dir() and not d.name.startswith(".") and d.name not in (
                "node_modules",
                "__pycache__",
                "venv",
                ".venv",
                "dist",
                "build",
                "target",
                ".tox",
            ):
                ctx.key_modules.append(d.name)

    def _stage4_standards(self, ctx: ScanContext) -> None:
        """Lint configs, formatter configs, git hooks, code style."""
        for lc in LINT_CONFIGS:
            p = ctx.root / lc
            if p.is_file() or p.is_dir():
                ctx.lint_configs.append(lc)
        for fc in FORMATTER_CONFIGS:
            p = ctx.root / fc
            if p.is_file():
                ctx.formatter_configs.append(fc)
        for gh in GIT_HOOK_PATHS:
            p = ctx.root / gh
            if p.is_file() or p.is_dir():
                ctx.git_hooks.append(gh)
        contributing = ctx.root / "CONTRIBUTING.md"
        if contributing.is_file():
            ctx.lint_configs.append("CONTRIBUTING.md")

    def _stage5_import_existing(self, ctx: ScanContext) -> None:
        """Read existing docs, ADRs, changelogs, KB."""
        max_import_files = _MAX_WALK_FILES
        for doc_dir in ["doc", "docs"]:
            p = ctx.root / doc_dir
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file() and not f.name.startswith("."):
                        ctx.existing_docs.append(str(f.relative_to(ctx.root)))
                        if len(ctx.existing_docs) >= max_import_files:
                            logger.warning(
                                "Import of existing docs capped at %d files", max_import_files,
                            )
                            break
        readme = ctx.root / "README.md"
        if readme.is_file():
            ctx.existing_docs.append("README.md")
        for adr_dir in ["doc/adr", "docs/adr"]:
            p = ctx.root / adr_dir
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        ctx.existing_adrs.append(str(f.relative_to(ctx.root)))
                        if len(ctx.existing_adrs) >= max_import_files:
                            logger.warning(
                                "Import of ADRs capped at %d files", max_import_files,
                            )
                            break
        for changelog_name in ["CHANGELOG.md", "CHANGELOG", "CHANGELOG.txt",
                                "RELEASE_NOTES.md", "RELEASE_NOTES"]:
            p = ctx.root / changelog_name
            if p.is_file():
                ctx.existing_changelogs.append(changelog_name)
        kb_dir = ctx.root / "doc" / "kb"
        if kb_dir.is_dir():
            ctx.existing_kb = True

    def _stage6_ai_analysis(self, ctx: ScanContext) -> None:
        """Try LLM analysis; skip gracefully if unavailable."""
        try:
            import importlib.util
            if not importlib.util.find_spec("sdlc.llm.client"):
                raise ImportError("sdlc.llm.client not found")
            summary = f"Project at {ctx.root}: languages={ctx.languages}, "
            summary += f"frameworks={ctx.frameworks}, build_tools={ctx.build_tools}"
            ctx.ai_summary = summary
        except (ImportError, Exception) as exc:
            warnings.warn(
                f"Stage 6 AI analysis skipped: {exc}",
                stacklevel=2,
            )
            ctx.ai_summary = None

    def _stage7_generate_result(self, ctx: ScanContext) -> ScanResult:
        """Build ScanResult with KB file suggestions and recommendations."""
        kb_files: dict[str, str] = {}
        recommendations: list[str] = []
        warn: list[str] = []
        next_steps: list[str] = []
        confidence = 0.0

        # conventions.md
        kb_files["conventions.md"] = "# Conventions\n\n<!-- Human-only: edit manually -->\n"

        # architecture/component-catalog.md
        components = "# Component Catalog\n\n"
        components += "## Languages\n\n"
        for lang, count in sorted(ctx.languages.items(), key=lambda x: -x[1]):
            components += f"- {lang}: {count} files\n"
        components += "\n## Frameworks\n\n"
        for fw in ctx.frameworks:
            components += f"- {fw}\n"
        components += "\n## Build Tools\n\n"
        for bt in ctx.build_tools:
            components += f"- {bt}\n"
        components += "\n## Entry Points\n\n"
        for ep in ctx.entry_points:
            components += f"- {ep}\n"
        components += "\n## Key Modules\n\n"
        for km in ctx.key_modules:
            components += f"- {km}\n"
        kb_files["architecture/component-catalog.md"] = components

        # architecture/deps.yaml
        deps_yaml_parts = ["components:"]
        for manifest_name, dep_list in ctx.dependencies.items():
            for dep in dep_list:
                deps_yaml_parts.append(f"  - name: {dep}")
                deps_yaml_parts.append(f"    source: {manifest_name}")
        deps_yaml = "\n".join(deps_yaml_parts) + "\n"
        kb_files["architecture/deps.yaml"] = deps_yaml

        # architecture/standards.md
        standards = "# Standards\n\n"
        if ctx.lint_configs:
            standards += "## Lint Configs\n\n"
            for lc in ctx.lint_configs:
                standards += f"- {lc}\n"
            standards += "\n"
        if ctx.formatter_configs:
            standards += "## Formatter Configs\n\n"
            for fc in ctx.formatter_configs:
                standards += f"- {fc}\n"
            standards += "\n"
        if ctx.git_hooks:
            standards += "## Git Hooks\n\n"
            for gh in ctx.git_hooks:
                standards += f"- {gh}\n"
            standards += "\n"
        kb_files["architecture/standards.md"] = standards

        # architecture/ci.md
        ci_md = "# CI/CD\n\n"
        if ctx.ci_configs:
            ci_md += "## CI Configs\n\n"
            for ci in ctx.ci_configs:
                ci_md += f"- {ci}\n"
            ci_md += "\n"
        if ctx.container_configs:
            ci_md += "## Container Configs\n\n"
            for cc in ctx.container_configs:
                ci_md += f"- {cc}\n"
            ci_md += "\n"
        kb_files["architecture/ci.md"] = ci_md

        # meta.json
        meta = {
            "languages": ctx.languages,
            "frameworks": ctx.frameworks,
            "build_tools": ctx.build_tools,
            "entry_points": ctx.entry_points,
            "ci_configs": ctx.ci_configs,
            "container_configs": ctx.container_configs,
        }
        kb_files["meta.json"] = json.dinternal-monitorings(meta, indent=2, ensure_ascii=False) + "\n"

        # Recommendations
        if "pom.xml" in ctx.manifests:
            pom_deps = ctx.manifests["pom.xml"].get("dependencies", [])
            if any("dong-boot" in d or "dongboot" in d for d in pom_deps):
                recommendations.append("dongboot adapter")
            else:
                recommendations.append("java adapter")
        if "pyproject.toml" in ctx.manifests or "requirements.txt" in ctx.manifests:
            recommendations.append("python adapter")
        if "package.json" in ctx.manifests:
            recommendations.append("node adapter")
        if "go.mod" in ctx.manifests:
            recommendations.append("go adapter")
        recommendations.append("new-feature profile")

        # Confidence
        factors = 0
        if ctx.languages:
            factors += 1
        if ctx.frameworks:
            factors += 1
        if ctx.manifests:
            factors += 1
        if ctx.entry_points:
            factors += 1
        if ctx.ci_configs:
            factors += 1
        confidence = min(factors / 5.0, 1.0)

        # Warnings
        if ctx.existing_kb:
            warn.append("Existing KB detected at doc/kb/; content will need merge")
        if not ctx.manifests:
            warn.append("No manifest files detected; tech stack may be incomplete")
        if not ctx.languages:
            warn.append("No source files detected; project may be empty")
        if ctx.ai_summary is None:
            warn.append("AI analysis skipped (no LLM client available)")

        # Next steps
        next_steps.append("Review generated KB files before proceeding")
        if ctx.existing_kb:
            next_steps.append("Merge existing KB content with new scan results")
        next_steps.append("Run `sdlc kb write` to persist KB files")

        return ScanResult(
            kb_files=kb_files,
            recommendations=recommendations,
            warnings=warn,
            confidence=confidence,
            next_steps=next_steps,
        )

    # ------------------------------------------------------------------
    # Async helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run_async(coro: Any) -> Any:
        """Run an async coroutine safely from synchronous context.

        Uses ``asyncio.run()`` when no event loop is running; otherwise
        schedules the coroutine via ``run_in_executor`` to avoid conflicts
        with an already-running loop.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            return asyncio.run(coro)

        # Already inside a running loop -- use executor to avoid nesting.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
