import hashlib
from pathlib import Path


def file_fingerprint(p: Path) -> str:
    if not p.exists():
        raise FileNotFoundError(str(p))
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dir_fingerprint(p: Path, glob: str = "**/*") -> str:
    if not p.exists():
        raise FileNotFoundError(str(p))
    paths = sorted(f for f in p.glob(glob) if f.is_file())
    if not paths:
        return hashlib.sha256(b"").hexdigest()
    concat = "".join(file_fingerprint(f) for f in paths)
    return hashlib.sha256(concat.encode()).hexdigest()
