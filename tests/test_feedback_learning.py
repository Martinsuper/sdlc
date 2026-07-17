"""Tests for M-A6 + M-D5 feedback learning loop (ADR store + feedback recorder)."""

from __future__ import annotations

from sdlc.eval.feedback import FeedbackRecorder, Signal
from sdlc.kb.adr import ADR, MIN_SAMPLES_FOR_EFFECT, ADRStore
from sdlc.kb.memory import MemoryL2


def _store(tmp_path) -> ADRStore:
    s = ADRStore(tmp_path)
    s.record(ADR(id="adr-1", decision="use JWT", made_by_agent="architect"))
    s.record(ADR(id="adr-2", decision="sessions in DB", made_by_agent="architect"))
    return s


# --------------------------------------------------------------------------- #
# ADR store
# --------------------------------------------------------------------------- #

def test_record_and_get_roundtrip(tmp_path):
    s = _store(tmp_path)
    assert s.get("adr-1").decision == "use JWT"
    assert len(s.all()) == 2


def test_record_replaces_by_id(tmp_path):
    s = _store(tmp_path)
    s.record(ADR(id="adr-1", decision="use OAuth", made_by_agent="architect"))
    assert s.get("adr-1").decision == "use OAuth"
    assert len(s.all()) == 2


def test_update_outcome_running_mean(tmp_path):
    s = _store(tmp_path)
    s.update_outcome("adr-1", "ok", 0.4)
    s.update_outcome("adr-1", "ok", 0.6)
    a = s.get("adr-1")
    assert a.sample_count == 2
    assert a.effect_score == 0.5  # mean of 0.4 and 0.6


def test_update_outcome_clamps(tmp_path):
    s = _store(tmp_path)
    s.update_outcome("adr-1", "incident", -1.0)
    s.update_outcome("adr-1", "incident", -1.0)
    assert s.get("adr-1").effect_score == -1.0


def test_update_outcome_unknown_adr(tmp_path):
    s = _store(tmp_path)
    assert s.update_outcome("nope", "x", 0.5) is None


# --------------------------------------------------------------------------- #
# Sample-count gate (noise guard)
# --------------------------------------------------------------------------- #

def test_effect_inactive_below_threshold(tmp_path):
    s = _store(tmp_path)
    s.update_outcome("adr-1", "incident", -1.0)  # 1 sample only
    assert not s.get("adr-1").effect_active
    _preferred, avoid = s.ranked_for_injection()
    # Not enough samples => excluded from both lists (baseline behavior).
    assert "adr-1" not in [a.id for a in avoid]


def test_effect_active_at_threshold(tmp_path):
    s = _store(tmp_path)
    for _ in range(MIN_SAMPLES_FOR_EFFECT):
        s.update_outcome("adr-1", "good", 0.5)
    a = s.get("adr-1")
    assert a.effect_active
    preferred, _ = s.ranked_for_injection()
    assert "adr-1" in [x.id for x in preferred]


def test_ranking_splits_preferred_and_avoid(tmp_path):
    s = _store(tmp_path)
    for _ in range(3):
        s.update_outcome("adr-1", "good", 0.6)
        s.update_outcome("adr-2", "bad", -0.8)
    preferred, avoid = s.ranked_for_injection()
    assert [a.id for a in preferred] == ["adr-1"]
    assert [a.id for a in avoid] == ["adr-2"]


# --------------------------------------------------------------------------- #
# FeedbackRecorder (M-D5 signal production)
# --------------------------------------------------------------------------- #

def test_incident_weighs_more_than_success(tmp_path):
    _store(tmp_path)
    fb = FeedbackRecorder(tmp_path)
    assert abs(fb.effect_delta("rollback")) > fb.effect_delta("deploy_success")


def test_record_signal_updates_adr(tmp_path):
    _store(tmp_path)
    fb = FeedbackRecorder(tmp_path)
    updated = fb.record_signal(Signal("adr-1", "adopted", "merged"))
    assert updated is not None
    assert updated.sample_count == 1
    assert updated.outcome == "merged"


def test_record_signal_unknown_kind(tmp_path):
    _store(tmp_path)
    fb = FeedbackRecorder(tmp_path)
    assert fb.record_signal(Signal("adr-1", "made_up_signal")) is None


def test_record_batch_report(tmp_path):
    _store(tmp_path)
    fb = FeedbackRecorder(tmp_path)
    report = fb.record_batch(
        [
            Signal("adr-1", "deploy_success"),
            Signal("nope", "deploy_success"),
            Signal("adr-2", "bogus"),
        ]
    )
    assert report.updated == ["adr-1"]
    assert report.unknown_adrs == ["nope"]
    assert report.unknown_signals == ["bogus"]


# --------------------------------------------------------------------------- #
# MemoryL2 consinternal-monitoringtion (M-A6)
# --------------------------------------------------------------------------- #

def test_memory_effect_ranked_decisions(tmp_path):
    _store(tmp_path)
    fb = FeedbackRecorder(tmp_path)
    for _ in range(3):
        fb.record_signal(Signal("adr-1", "deploy_success"))
        fb.record_signal(Signal("adr-2", "rollback"))
    m = MemoryL2(kb_root=tmp_path)
    ranked = m.effect_ranked_decisions()
    assert [d["id"] for d in ranked["preferred"]] == ["adr-1"]
    assert [d["id"] for d in ranked["avoid"]] == ["adr-2"]


def test_memory_no_kb_root_returns_empty():
    m = MemoryL2(kb_root=None)
    ranked = m.effect_ranked_decisions()
    assert ranked == {"preferred": [], "avoid": []}
