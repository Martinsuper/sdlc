#!/usr/bin/env bash
#
# sync-opencode.sh — 把本仓库的 sdlc skill 和命令同步到 OpenCode。
#
# 用法:
#   scripts/sync-opencode.sh            # 同步到全局 OpenCode 配置目录
#   scripts/sync-opencode.sh --dry-run  # 只预览会改什么
#
# 可通过 OPENCODE_CONFIG_DIR 覆盖默认目标 ~/.config/opencode。
# 同步后需重启 OpenCode 才会重新加载 skill 和命令。

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
SKILL_DEST="$CONFIG_DIR/skills/sdlc"
COMMAND_DEST="$CONFIG_DIR/commands/sdlc"
DRY_RUN=""

if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN="--dry-run"
elif [ -n "${1:-}" ]; then
  printf '不支持的参数: %s\n' "$1" >&2
  exit 2
fi

printf '源(仓库): %s\n' "$REPO_ROOT"
printf '目标(skill): %s\n' "$SKILL_DEST"
printf '目标(commands): %s\n' "$COMMAND_DEST"
[ -n "$DRY_RUN" ] && printf '模式: 预览(--dry-run, 不落盘)\n'
printf '\n'

SYNC_SKILL_DEST="$SKILL_DEST"
SYNC_COMMAND_DEST="$COMMAND_DEST"
if [ -n "$DRY_RUN" ] && { [ ! -d "$SKILL_DEST" ] || [ ! -d "$COMMAND_DEST" ]; }; then
  PREVIEW_ROOT="$(mktemp -d)"
  trap 'rm -rf "$PREVIEW_ROOT"' EXIT
  SYNC_SKILL_DEST="$PREVIEW_ROOT/skills/sdlc"
  SYNC_COMMAND_DEST="$PREVIEW_ROOT/commands/sdlc"
  mkdir -p "$SYNC_SKILL_DEST" "$SYNC_COMMAND_DEST"
elif [ -z "$DRY_RUN" ]; then
  mkdir -p "$SKILL_DEST" "$COMMAND_DEST"
fi

RSYNC_COMMON=(-a --delete --itemize-changes)
[ -n "$DRY_RUN" ] && RSYNC_COMMON+=(--dry-run)

rsync "${RSYNC_COMMON[@]}" \
  --include=/SKILL.md \
  --include=/references/*** \
  --include=/overlays/*** \
  --include=/templates/*** \
  --exclude=* \
  "$REPO_ROOT/" "$SYNC_SKILL_DEST/"

rsync "${RSYNC_COMMON[@]}" \
  "$REPO_ROOT/commands/sdlc/" "$SYNC_COMMAND_DEST/"

printf '\n'
if [ -n "$DRY_RUN" ]; then
  printf '预览完成。去掉 --dry-run 后执行实际同步。\n'
else
  printf '同步完成。请退出并重启 OpenCode，然后使用 /sdlc/init、/sdlc/design 等命令。\n'
fi
