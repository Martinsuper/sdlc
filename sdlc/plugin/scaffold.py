"""Plugin scaffolding (M-C1): generate a ready-to-edit plugin skeleton.

`sdlc plugin new <type> <name>` writes a plugin.json manifest plus a commented
entry YAML matching that extension type's real schema, so a contributor can go
from zero to a validating plugin by filling in the blanks.
"""

from __future__ import annotations

from pathlib import Path

from sdlc.plugin.manifest import MANIFEST_FILENAME, PLUGIN_TYPES, PluginManifest

# Commented starter YAML per plugin type. Each mirrors the shape the matching
# sdlc registry loads, so the scaffold output validates out of the box.
_TEMPLATES: dict[str, str] = {
    "adapter": (
        "# Adapter: maps a tech stack to components sdlc understands.\n"
        "id: {name}\n"
        "name: {name}\n"
        "version: \"1.0\"\n"
        "language: \"\"          # e.g. python, java, go\n"
        "framework: \"\"         # e.g. fastapi, spring-boot\n"
        "components: []          # list of {{id, type, detect, enforce}}\n"
    ),
    "profile": (
        "# Profile: an ordered workflow of stages for an entry kind.\n"
        "id: {name}\n"
        "name: {name}\n"
        "entry_kinds: []         # e.g. [feature]\n"
        "base_stages: []         # ordered stage ids\n"
        "severity: P2\n"
    ),
    "stage": (
        "# Stage: one step in a pipeline, executed by a subagent.\n"
        "id: {name}\n"
        "name: {name}\n"
        "category: impl\n"
        "subagent: \"\"\n"
        "produces_artifacts: []\n"
    ),
    "rule-set": (
        "# Rule set: MUST/SHOULD constraints enforced during stages.\n"
        "rules:\n"
        "  - id: {name}-001\n"
        "    level: MUST         # MUST | SHOULD | MAY\n"
        "    description: \"\"\n"
    ),
    "subagent": (
        "# Subagent: a role with a model, tools, and prompt.\n"
        "id: {name}\n"
        "name: {name}\n"
        "role: \"\"\n"
        "model: claude-sonnet-4-20250514\n"
        "tools: [read, write]\n"
        "prompt: \"\"\n"
    ),
    "gate": (
        "# Gate: an approval checkpoint after a stage.\n"
        "id: {name}\n"
        "name: {name}\n"
        "after_stage: \"\"\n"
        "trigger: always\n"
        "reviewer: \"\"\n"
    ),
    "skill": (
        "# Skill: a reusable tool/capability a subagent can invoke.\n"
        "id: {name}\n"
        "name: {name}\n"
        "description: \"\"\n"
        "entrypoint: \"\"        # module:function\n"
    ),
}


def scaffold(plugin_type: str, name: str, dest: Path, author: str = "") -> Path:
    """Create a new plugin skeleton under ``dest/<name>`` and return its dir.

    Raises ValueError for an unknown type or a destination that already exists
    (never clobbers existing work)."""
    if plugin_type not in PLUGIN_TYPES:
        raise ValueError(f"Unknown plugin type {plugin_type!r}; must be one of {PLUGIN_TYPES}")
    if not name or "/" in name or name.startswith("."):
        raise ValueError(f"Invalid plugin name: {name!r}")

    plugin_dir = dest / name
    if plugin_dir.exists():
        raise ValueError(f"Destination already exists: {plugin_dir}")
    plugin_dir.mkdir(parents=True)

    entry = "plugin.yaml"
    manifest = PluginManifest(
        id=name,
        type=plugin_type,
        version="0.1.0",
        sdlc_version=">=2.0,<3.0",
        author=author,
        description=f"A {plugin_type} plugin.",
        entry=entry,
    )
    (plugin_dir / MANIFEST_FILENAME).write_text(manifest.to_json() + "\n", encoding="utf-8")
    (plugin_dir / entry).write_text(_TEMPLATES[plugin_type].format(name=name), encoding="utf-8")
    return plugin_dir
