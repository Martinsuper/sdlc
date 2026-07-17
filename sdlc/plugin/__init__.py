"""Plugin SDK (M-C1): scaffold, validate, and pack sdlc extensions.

Adds tooling around sdlc's existing zero-code YAML extension model so
contributors can go from an idea to a distributable, validated plugin quickly —
the supply side of the marketplace (M-C2).
"""

from sdlc.plugin.manifest import PLUGIN_TYPES, PluginManifest
from sdlc.plugin.packer import pack, read_manifest_from_pkg
from sdlc.plugin.scaffold import scaffold
from sdlc.plugin.validator import PluginValidator, ValidationReport

__all__ = [
    "PLUGIN_TYPES",
    "PluginManifest",
    "PluginValidator",
    "ValidationReport",
    "pack",
    "read_manifest_from_pkg",
    "scaffold",
]
