---
description: 需求澄清 - 识别需求模糊点、分两轮追问、固化为结构化功能规格。转调 sdlc skill 的 clarify 阶段。
argument-hint: [需求描述或PRD链接]
allowed-tools: Read, Write, Edit, Bash, Skill, mcp__document-reader__read_jd_doc
---

# SDLC 需求澄清

请执行 `sdlc` skill 的 **clarify（需求澄清）** 阶段来处理本次请求。

## 执行方式

1. 通过 Skill 工具调用 `sdlc` skill（若已加载则直接按其说明工作）。
2. 读取该 skill 的 `references/clarify.md`，严格按其 **输入 → 前置检查 → 执行 → 产出 → 交接** 骨架执行。
3. 用户输入 `$ARGUMENTS` 作为待澄清的需求描述或 PRD 链接。
4. **只描述客观需求，不涉及任何方案设计**：只写"要什么/做成什么样/怎样算对"，不写技术选型、架构、库表、接口、算法、代码——那是 design 阶段的事（详见 skill 的边界红线）。
5. 产物写入 `.sdlc/01-prd/00-<需求名>.md`（文件名的 `<需求名>` 取自需求名称、压缩成无空格短名，**勿用 `requirements` 这类阶段通用词**；后续 design/review 等阶段沿用同一需求名），遵循 skill 定义的目录与命名规约。

> 本命令是薄封装：澄清的全部逻辑以 `sdlc` skill 的 `references/clarify.md` 为**单一来源**，此文件不重复维护澄清清单，避免两套内容漂移。
