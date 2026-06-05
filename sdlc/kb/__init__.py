"""sdlc.kb — Knowledge-base engine."""

from sdlc.kb.fingerprint import compute_kb_fingerprint, compute_layer_fingerprint
from sdlc.kb.knowledge_base import KBFileNotFoundError, KnowledgeBase
from sdlc.kb.models import KBDeltaResult, KBLayer, ScanResult
from sdlc.kb.reconciler import Reconciler
from sdlc.kb.scanner import Scanner
from sdlc.kb.writer import KBWriter

__all__ = [
    "KBDeltaResult",
    "KBFileNotFoundError",
    "KBLayer",
    "KBWriter",
    "KnowledgeBase",
    "Reconciler",
    "ScanResult",
    "Scanner",
    "compute_kb_fingerprint",
    "compute_layer_fingerprint",
]
