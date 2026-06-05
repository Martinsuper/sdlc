"""sdlc.utils — foundational utilities with no business dependencies."""

from sdlc.utils.config import LLMConfig, ProfileConfig, SdlcConfig
from sdlc.utils.config_loader import get_config_dir, load_config, save_config
from sdlc.utils.exceptions import (
    AdapterNotFoundError,
    ConfigError,
    EntryDetectionError,
    KBWriteConflictError,
    LLMError,
    PipelineBuildError,
    ResumeExpiredError,
    RuleViolationError,
    SdlcError,
    StageExecutionError,
)
from sdlc.utils.fingerprint import dir_fingerprint, file_fingerprint
from sdlc.utils.git import git_commit, git_current_branch, git_diff, git_root, is_git_repo
from sdlc.utils.logging import get_logger, log_event
from sdlc.utils.paths import ensure_dir, project_root, sdlc_home
from sdlc.utils.text import normalize, slugify, trim
from sdlc.utils.time import format_iso, human_delta, now_utc, parse_timespec
from sdlc.utils.yaml_io import load_yaml, load_yaml_str, save_yaml

__all__ = [
    "AdapterNotFoundError",
    "ConfigError",
    "EntryDetectionError",
    "KBWriteConflictError",
    "LLMConfig",
    "LLMError",
    "PipelineBuildError",
    "ProfileConfig",
    "ResumeExpiredError",
    "RuleViolationError",
    "SdlcConfig",
    "SdlcError",
    "StageExecutionError",
    "dir_fingerprint",
    "ensure_dir",
    "file_fingerprint",
    "format_iso",
    "get_config_dir",
    "get_logger",
    "git_commit",
    "git_current_branch",
    "git_diff",
    "git_root",
    "human_delta",
    "is_git_repo",
    "load_config",
    "load_yaml",
    "load_yaml_str",
    "log_event",
    "normalize",
    "now_utc",
    "parse_timespec",
    "project_root",
    "save_config",
    "save_yaml",
    "sdlc_home",
    "slugify",
    "trim",
]
