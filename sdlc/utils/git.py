import subprocess
from pathlib import Path


def _resolve(p: Path | None) -> Path:
    return Path.cwd() if p is None else Path(p).resolve()


def is_git_repo(p: Path | None = None) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(_resolve(p)),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def git_root(p: Path | None = None) -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(_resolve(p)),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    root = result.stdout.strip()
    return Path(root) if root else None


def git_current_branch(p: Path | None = None) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(_resolve(p)),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch if branch else None


def git_diff(p: Path | None = None, staged: bool = False) -> str:
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--cached")
    result = subprocess.run(
        cmd,
        cwd=str(_resolve(p)),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def git_commit(msg: str, p: Path | None = None) -> bool:
    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=str(_resolve(p)),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0
