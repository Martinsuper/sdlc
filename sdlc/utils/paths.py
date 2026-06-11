import logging
import tempfile
from pathlib import Path

from sdlc.utils.exceptions import ConfigError

logger = logging.getLogger(__name__)


def sdlc_home() -> Path:
    p = Path.home() / ".sdlc"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback = Path(tempfile.gettempdir()) / ".sdlc"
        logger.warning(
            "Cannot create %s, using fallback directory %s", p, fallback
        )
        try:
            fallback.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Last resort: just return the path and let the caller handle it
            logger.warning("Cannot create fallback directory %s either", fallback)
        return fallback
    return p


def project_root(start: Path | None = None) -> Path:
    current = Path(start).resolve() if start else Path.cwd()
    while True:
        if (current / ".sdlc").is_dir() or (current / "pyproject.toml").is_file():
            return current
        parent = current.parent
        if parent == current:
            raise ConfigError(f"No project root found from {start or Path.cwd()}")
        current = parent


def ensure_dir(p: Path, mode: int = 0o755) -> Path:
    """Create directory with the given mode (default 0o755, not overly permissive 0o777)."""
    p.mkdir(parents=True, exist_ok=True, mode=mode)
    # mkdir with mode may be affected by the umask; chmod ensures the mode is exact
    if p.is_dir():
        try:
            p.chmod(mode)
        except OSError:
            pass  # best-effort; on some platforms chmod may fail (e.g. ACLs)
    return p
