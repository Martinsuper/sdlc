---
description: 设计文档AI评审 - 探测画像后按适用维度逐项检查,输出Pass/Warning/Block与P0-P3风险分级。转调 sdlc skill 的 review 阶段。
argument-hint: [设计文档路径]
allowed-tools: Read, Write, Edit, Bash, Skill, mcp__document-reader__read_jd_doc
---

# SDLC 设计评审

请执行 `sdlc` skill 的 **review（设计评审）** 阶段来处理本次请求。

## 执行方式

1. 通过 Skill 工具调用 `sdlc` skill。
2. 先读 `references/profiles.md` 探测画像,得出启用的评审维度（未启用标签的维度整维跳过,不产生噪音）。
3. 读 `references/review.md`,严格按其骨架逐维度评审;用 `templates/review-report.md` 组织报告。
4. 用户输入 `$ARGUMENTS` 作为被评审的设计文档路径。
5. 产物写入 `.sdlc/03-review/00-<需求名>.md`（`<需求名>` 沿用 PRD/设计的需求名，勿用 `review` 通用词；命名规约见 skill）。

> 本命令是薄封装:评审维度与裁剪规则以 `sdlc` skill 为**单一来源**,此文件不重复维护 checklist,避免旧版企业专用维度对通用项目产生噪音。
