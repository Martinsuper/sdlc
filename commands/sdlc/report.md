---
description: 生成项目/代码分析报告 - 现场扫描代码库做统计度量分析（结构/接口/依赖影响等），产出留档到 .sdlc/<数字>-report/。转调 sdlc skill 的 report 阶段。
argument-hint: [可选:主题 structure|api|deps|complexity 或自然语言]
allowed-tools: Read, Write, Edit, Bash, Skill, mcp__codegraph__codegraph_explore, mcp__codegraph__codegraph_files, mcp__codegraph__codegraph_search, mcp__codegraph__codegraph_callers, mcp__codegraph__codegraph_callees, mcp__codegraph__codegraph_impact
---

# SDLC 项目/代码分析报告

请执行 `sdlc` skill 的 **report（项目/代码分析报告）** 阶段来处理本次请求。

## 执行方式

1. 通过 Skill 工具调用 `sdlc` skill（若已加载则直接按其说明工作）。
2. 读该 skill 的 `references/report.md`，严格按其 **输入 → 前置检查 → 执行 → 产出 → 交接** 骨架执行。
3. 优先用 codegraph（`.codegraph/` 就绪时）取数，未就绪则降级用 `find`/`grep`/Read 静态扫描；先读 `references/profiles.md` 探测项目画像，据此裁剪报告维度。
4. 用户输入 `$ARGUMENTS` 作为报告主题：`structure`（结构）/ `api`|`interface`（接口）/ `deps`|`impact`（依赖与影响）/ `complexity`（复杂度）或自然语言主题；无参数则做综合报告。
5. 报告落到 `.sdlc/<数字>-report/<数字>-<主题名>.md`，目录名与文件名均以数字前缀开头（遵循 skill 的产物目录规约）。

> 本命令是薄封装：报告分析逻辑与目录规约以 `sdlc` skill 的 `references/report.md` 为**单一来源**，此文件不重复维护。
