"""Safe file read/write operations with path validation."""

from __future__ import annotations

import stat
from pathlib import Path

from sdlc.utils.paths import ensure_dir


class FileSystem:
    """Safe file operations with path validation."""

    @staticmethod
    def read_file(path: Path, encoding: str = "utf-8") -> str:
        """Read file content. Validates path exists and is a file."""
        resolved = path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Path does not exist: {resolved}")
        if not resolved.is_file():
            raise ValueError(f"Path is not a file: {resolved}")
        return resolved.read_text(encoding=encoding)

    @staticmethod
    def write_file(path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write content to file. Creates parent directories."""
        resolved = path.resolve()
        ensure_dir(resolved.parent)
        resolved.write_text(content, encoding=encoding)

    @staticmethod
    def list_files(directory: Path, pattern: str = "**/*") -> list[Path]:
        """List files matching glob pattern."""
        resolved = directory.resolve()
        if not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {resolved}")
        return sorted(p for p in resolved.glob(pattern) if p.is_file())

    @staticmethod
    def file_info(path: Path) -> dict[str, object]:
        """Get file metadata: size, modified time, etc."""
        resolved = path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Path does not exist: {resolved}")
        if not resolved.is_file():
            raise ValueError(f"Path is not a file: {resolved}")
        st = resolved.stat()
        return {
            "path": str(resolved),
            "size": st.st_size,
            "modified": st.st_mtime,
            "mode": stat.filemode(st.st_mode),
            "is_file": resolved.is_file(),
        }
