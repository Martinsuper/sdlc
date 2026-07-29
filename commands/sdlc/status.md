---
description: 查看SDLC进度 - 扫描 .sdlc/ 下各数字前缀阶段目录,汇总研发进度到哪一步。转调 sdlc skill 的 status 阶段。
argument-hint: [可选:阶段名 design|review|deploy]
allowed-tools: Read, Bash, Skill
---

# SDLC 状态查看

请执行 `sdlc` skill 的 **status（状态查看）** 阶段来处理本次请求。

## 执行方式

1. 通过 Skill 工具调用 `sdlc` skill。
2. 读 `references/status.md`,按其扫描 `.sdlc/` 下 `00-context/`(上下文资料) 与 `01-prd/ ~ 06-deploy/` 各阶段目录,输出进度摘要(纯只读)。
3. 用户输入 `$ARGUMENTS` 若指定阶段名,只显示该阶段。

> 本命令是薄封装:扫描逻辑以 `sdlc` skill 为**单一来源**。
