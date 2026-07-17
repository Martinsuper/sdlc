"""Tests for M-C2/C3 marketplace + CI integration.

Covered: registry search/ranking, checksum trust, installer roundtrip (build a
package with the M-C1 packer, install, verify layout), market CLI, run
--format json, and PR-comment formatting.

VERIFICATION BOUNDARY: real registry hosting, network downloads, and live
GitHub Action execution require an external environment and are not covered.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from sdlc.market.installer import install_package
from sdlc.market.registry_client import RegistryClient
from sdlc.market.trust import compute_checksum, verify_checksum
from sdlc.plugin.packer import pack
from sdlc.plugin.scaffold import scaffold


def _registry_file(tmp_path: Path) -> Path:
    data = {
        "schema_version": "1",
        "plugins": [
            {"id": "adapter-django", "type": "adapter", "version": "1.2.0",
             "author": "community/x", "verified": False, "downloads": 50},
            {"id": "adapter-spring", "type": "adapter", "version": "2.0.0",
             "author": "official", "verified": True, "downloads": 500},
            {"id": "profile-mobile", "type": "profile", "version": "1.0.0", "downloads": 10},
        ],
    }
    p = tmp_path / "index.json"
    p.write_text(json.dinternal-monitorings(data), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

def test_search_ranks_verified_and_popular_first(tmp_path):
    client = RegistryClient(str(_registry_file(tmp_path)))
    results = client.search("adapter")
    # verified official (spring) ranks above unverified (django).
    assert results[0].id == "adapter-spring"


def test_search_type_filter(tmp_path):
    client = RegistryClient(str(_registry_file(tmp_path)))
    results = client.search("", type_filter="profile")
    assert [e.id for e in results] == ["profile-mobile"]


def test_find_by_id(tmp_path):
    client = RegistryClient(str(_registry_file(tmp_path)))
    assert client.find("adapter-django").version == "1.2.0"
    assert client.find("nope") is None


# --------------------------------------------------------------------------- #
# Trust
# --------------------------------------------------------------------------- #

def test_checksum_match(tmp_path):
    f = tmp_path / "pkg"
    f.write_bytes(b"hello")
    good = compute_checksum(b"hello")
    assert verify_checksum(f, good)
    assert not verify_checksum(f, "sha256:deadbeef")


def test_empty_checksum_is_unverifiable(tmp_path):
    f = tmp_path / "pkg"
    f.write_bytes(b"x")
    assert not verify_checksum(f, "")


# --------------------------------------------------------------------------- #
# Installer roundtrip (build with M-C1 packer, install)
# --------------------------------------------------------------------------- #

def test_install_roundtrip(tmp_path):
    plugin_dir = scaffold("adapter", "demo-market", tmp_path / "src")
    archive = pack(plugin_dir, tmp_path / "out")
    dest = install_package(archive, dest=tmp_path / "ext")
    assert (dest / "plugin.json").exists()
    assert dest.name == "demo-market"


def test_install_rejects_bad_checksum(tmp_path):
    from sdlc.market.registry_client import RegistryEntry
    from sdlc.market.trust import TrustError

    plugin_dir = scaffold("adapter", "demo2", tmp_path / "src")
    archive = pack(plugin_dir, tmp_path / "out")
    entry = RegistryEntry(id="demo2", type="adapter", version="0.1.0", checksum="sha256:wrong")
    with pytest.raises(TrustError):
        install_package(archive, entry=entry, dest=tmp_path / "ext")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def test_market_search_cli(tmp_path):
    from sdlc.cli.market_cmd import market

    r = CliRunner().invoke(market, ["search", "adapter", "--registry", str(_registry_file(tmp_path))])
    assert r.exit_code == 0
    assert "adapter-spring" in r.output


def test_run_format_json_smoke():
    # The --format json option must be wired; a full run needs an LLM, so just
    # assert the option exists on the command.
    from sdlc.cli.run_cmd import run

    opt_names = {p.name for p in run.params}
    assert "output_format" in opt_names


# --------------------------------------------------------------------------- #
# CI comment formatting (M-C3)
# --------------------------------------------------------------------------- #

def _load_comment_module():
    path = Path(".github/actions/sdlc-review/comment.py")
    spec = importlib.util.spec_from_file_location("sdlc_review_comment", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_comment_formats_failure():
    mod = _load_comment_module()
    body = mod.format_comment(
        {"status": "failed", "error": "boom", "stages": [{"id": "cr", "status": "FAILED", "error": "x"}],
         "cost_usd": 0.12}
    )
    assert "failed" in body
    assert "boom" in body
    assert "| cr |" in body


def test_comment_formats_success():
    mod = _load_comment_module()
    body = mod.format_comment({"status": "completed", "stages": [], "cost_usd": 0.0})
    assert "completed" in body
