"""Tests for the M-C1 plugin SDK (sdlc/plugin/)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sdlc.plugin.manifest import PLUGIN_TYPES, PluginManifest
from sdlc.plugin.packer import pack, read_manifest_from_pkg
from sdlc.plugin.scaffold import scaffold
from sdlc.plugin.validator import PluginValidator

# --------------------------------------------------------------------------- #
# Scaffold + validate loop (every type)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("ptype", sorted(PLUGIN_TYPES))
def test_scaffold_then_validate(ptype, tmp_path):
    plugin_dir = scaffold(ptype, f"demo-{ptype.replace('-', '')}", tmp_path)
    report = PluginValidator(sdlc_version="2.0.0").validate(plugin_dir)
    assert report.ok, f"{ptype} scaffold should validate: {report.errors}"


def test_scaffold_rejects_unknown_type(tmp_path):
    with pytest.raises(ValueError, match="Unknown plugin type"):
        scaffold("nonsense", "x", tmp_path)


def test_scaffold_refuses_to_clobber(tmp_path):
    scaffold("adapter", "dup", tmp_path)
    with pytest.raises(ValueError, match="already exists"):
        scaffold("adapter", "dup", tmp_path)


def test_scaffold_rejects_bad_name(tmp_path):
    with pytest.raises(ValueError, match="Invalid plugin name"):
        scaffold("adapter", "a/b", tmp_path)


# --------------------------------------------------------------------------- #
# Validator
# --------------------------------------------------------------------------- #

def test_validate_missing_manifest(tmp_path):
    report = PluginValidator().validate(tmp_path)
    assert not report.ok
    assert any("plugin.json" in e for e in report.errors)


def test_validate_missing_required_key(tmp_path):
    plugin_dir = scaffold("profile", "p1", tmp_path)
    # Profile requires base_stages; remove it.
    entry = plugin_dir / "plugin.yaml"
    entry.write_text("id: p1\nname: p1\n", encoding="utf-8")
    report = PluginValidator(sdlc_version="2.0.0").validate(plugin_dir)
    assert not report.ok
    assert any("base_stages" in e for e in report.errors)


def test_validate_bad_sdlc_specifier(tmp_path):
    plugin_dir = scaffold("adapter", "p2", tmp_path)
    m = PluginManifest.load(plugin_dir)
    m.sdlc_version = "not-a-spec"
    (plugin_dir / "plugin.json").write_text(m.to_json(), encoding="utf-8")
    report = PluginValidator().validate(plugin_dir)
    assert not report.ok
    assert any("specifier" in e for e in report.errors)


def test_validate_incompatible_version_warns(tmp_path):
    plugin_dir = scaffold("adapter", "p3", tmp_path)  # sdlc_version >=2.0,<3.0
    report = PluginValidator(sdlc_version="1.1.0").validate(plugin_dir)
    assert report.ok  # a version mismatch is a warning, not a hard error
    assert any("does not satisfy" in w for w in report.warnings)


# --------------------------------------------------------------------------- #
# Packer
# --------------------------------------------------------------------------- #

def test_pack_roundtrip_embeds_checksum(tmp_path):
    plugin_dir = scaffold("adapter", "packme", tmp_path)
    archive = pack(plugin_dir, tmp_path / "out")
    assert archive.exists()
    assert archive.name == "packme-0.1.0.sdlcpkg"
    m = read_manifest_from_pkg(archive)
    assert m.checksum.startswith("sha256:")
    assert m.id == "packme"


def test_pack_refuses_invalid_plugin(tmp_path):
    plugin_dir = scaffold("profile", "bad", tmp_path)
    (plugin_dir / "plugin.yaml").write_text("id: bad\n", encoding="utf-8")  # missing base_stages
    with pytest.raises(ValueError, match="failed validation"):
        pack(plugin_dir, tmp_path / "out")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def test_cli_new_validate_pack(tmp_path):
    from sdlc.cli.plugin_cmd import plugin

    runner = CliRunner()
    r_new = runner.invoke(plugin, ["new", "adapter", "clidemo", "--dest", str(tmp_path)])
    assert r_new.exit_code == 0, r_new.output

    plugin_dir = tmp_path / "clidemo"
    r_val = runner.invoke(plugin, ["validate", str(plugin_dir)])
    assert r_val.exit_code == 0
    assert "valid" in r_val.output.lower()

    r_pack = runner.invoke(plugin, ["pack", str(plugin_dir), "--out", str(tmp_path / "o")])
    assert r_pack.exit_code == 0
    assert "Packed" in r_pack.output


def test_cli_validate_bad_exit_nonzero(tmp_path):
    from sdlc.cli.plugin_cmd import plugin

    r = CliRunner().invoke(plugin, ["validate", str(tmp_path)])  # no manifest
    assert r.exit_code == 1
