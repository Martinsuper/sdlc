"""Safe file read/write operations with path validation."""

from __future__ import annotations

import stat
from pathlib import Path

from sdlc.utils.paths import ensure_dir


class FileSystem:
    """Safe file operations with path validation.

    All file paths are validated to ensure they resolve inside the
    configured *project_root* directory, preventing path-traversal
    attacks.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = (project_root or Path.cwd()).resolve()

    def _validate_path(self, path: Path) -> Path:
        """Resolve *path* and verify it stays inside the project root."""
        resolved = path.resolve()
        try:
            resolved.relative_to(self._project_root)
        except ValueError:
            raise ValueError(
                f"Path escapes project root: {path} (resolved to {resolved}, "
                f"root is {self._project_root})"
            ) from None
        return resolved

    def read_file(self, path: Path, encoding: str = "utf-8") -> str:
        """Read file content. Validates path exists and is a file."""
        resolved = self._validate_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Path does not exist: {resolved}")
        if not resolved.is_file():
            raise ValueError(f"Path is not a file: {resolved}")
        return resolved.read_text(encoding=encoding)

    def write_file(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write content to file. Creates parent directories."""
        resolved = self._validate_path(path)
        ensure_dir(resolved.parent)
        resolved.write_text(content, encoding=encoding)

    def list_files(self, directory: Path, pattern: str = "**/*") -> list[Path]:
        """List files matching glob pattern."""
        resolved = self._validate_path(directory)
        if not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {resolved}")
        return sorted(p for p in resolved.glob(pattern) if p.is_file())

    def file_info(self, path: Path) -> dict[str, object]:
        """Get file metadata: size, modified time, etc."""
        resolved = self._validate_path(path)
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
