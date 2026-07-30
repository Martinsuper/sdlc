---
description: 编码实现 - 从评审通过的设计拆解开发单元、逐单元实现并自检(code-review/verify)。转调 sdlc skill 的 code 阶段。
argument-hint: [设计文档路径 | 数字前缀如01 | 指定改动点]
allowed-tools: Read, Write, Edit, MultiEdit, Bash, Skill
---

# SDLC 编码实现

请执行 `sdlc` skill 的 **code（编码实现）** 阶段来处理本次请求。

## 执行方式

1. 通过 Skill 工具调用 `sdlc` skill。
2. 读 `references/code.md`，严格按其 **输入 → 前置检查 → 执行 → 产出 → 交接** 骨架执行。
3. **前置门禁**：`.sdlc/02-design/` 下有设计文档、`.sdlc/03-review/` 下有评审报告（均扫描目录定位 `00-<需求名>.md`）且评审结论为「通过」；否则默认拦截，除非用户显式声明知风险强制跳过。
4. 遵循项目既有规范（`CLAUDE.md`、lint 配置）与 `.sdlc/00-context/` 的架构约定；只做设计要求的改动，逐单元用 `code-review`/`verify` skill 自检。
5. 用户输入 `$ARGUMENTS` 作为设计文档路径、数字前缀（如 `01`，选中 `02-design/01-*.md`，评审报告取同前缀）或指定改动点。
6. 主产出是代码变更本身；可选 `.sdlc/04-code/00-<需求名>.md` 仅在有设计外决策/权衡值得留痕时写。

> 本命令是薄封装：编码纪律、门禁、自检方式以 `sdlc` skill 为**单一来源**，具体编码交由 Claude Code 本体能力完成，此文件不重复维护。
