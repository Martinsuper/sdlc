---
description: 需求归档 - 列出可归档需求供选择,把所选需求的全部关联文档搬到 .sdlc/_archive/。转调 sdlc skill 的 archive 阶段。
---

# SDLC 需求归档

请执行 `sdlc` skill 的 **archive（归档）** 阶段来处理本次请求。

## 执行方式

1. 通过 Skill 工具调用 `sdlc` skill。
2. 读 `references/archive.md`，严格按其 **输入 → 前置检查 → 执行 → 产出 → 交接** 骨架执行。
3. 先探测 `.sdlc/` 布局（单需求 / 多 slug），**列出可归档需求供用户选择**（读各需求 PRD 元信息拿需求名与进展）。
4. 用户选定后展示归档清单，把该需求全部阶段文档搬到 `.sdlc/_archive/<需求名>-<日期>/`（git 仓库内优先 `git mv`）。`00-context/` 与已有 `_archive/` 不作为候选。
5. 用户输入 `$ARGUMENTS` 若指定需求名/slug，直接定位、跳过选择列表。

> 本命令是薄封装：归档布局探测与搬动逻辑以 `sdlc` skill 的 `references/archive.md` 为**单一来源**，此文件不重复维护。
