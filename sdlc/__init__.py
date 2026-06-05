"""sdlc - AI-driven full-lifecycle SDLC orchestration CLI tool."""

__version__ = "1.0.0"


def __getattr__(name: str) -> object:
    """Lazy import for heavy submodules.

    ``from sdlc import SdlcClient`` is supported but the import is deferred
    until the first actual access, so ``import sdlc`` (and accessing
    ``sdlc.__version__``) does not pull in the full dependency tree.
    """
    if name == "SdlcClient":
        from sdlc.client import SdlcClient

        return SdlcClient
    raise AttributeError(f"module 'sdlc' has no attribute {name!r}")


__all__ = ["SdlcClient"]
