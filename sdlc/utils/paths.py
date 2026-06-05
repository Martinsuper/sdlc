from pathlib import Path

from sdlc.utils.exceptions import ConfigError


def sdlc_home() -> Path:
    p = Path.home() / ".sdlc"
    p.mkdir(parents=True, exist_ok=True)
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


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p
