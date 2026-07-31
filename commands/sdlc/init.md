---
description: 项目前置准备 - codegraph 初始化 + 文档合规检查 + 散落文档归位(先出方案再动手)。转调 sdlc skill 的 init 阶段。
---

# SDLC 项目初始化

请执行 `sdlc` skill 的 **init（前置准备）** 阶段来处理本次请求。

## 执行方式

1. 通过 Skill 工具调用 `sdlc` skill（若已加载则直接按其说明工作）。
2. 读该 skill 的 `references/init.md`，严格按其 **输入 → 前置检查 → 执行 → 产出 → 交接** 骨架执行。
3. 用户输入 `$ARGUMENTS` 作为可选参数：`codegraph`（只做索引初始化）/ `docs`|`check`（只做文档合规检查与归位方案）；无参数则做完整前置准备。
4. 文档整理遵循"先出方案、逐项确认后再移动"，不擅自移动用户文件；目录/命名规约以 skill 的产物目录规约为准。

> 本命令是薄封装：初始化与文档整理逻辑以 `sdlc` skill 的 `references/init.md` 为**单一来源**，此文件不重复维护。
