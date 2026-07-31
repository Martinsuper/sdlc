---
description: 后端/前端/通用设计文档生成 - 探测项目画像并裁剪不适用章节,多图少文字(PlantUML),挂载 overlay 时补全企业专有章节。转调 sdlc skill 的 design 阶段。
---

# SDLC 方案设计

请执行 `sdlc` skill 的 **design（方案设计）** 阶段来处理本次请求。

## 执行方式

1. 通过 Skill 工具调用 `sdlc` skill。
2. 先读 `references/profiles.md` 探测项目画像与章节标签（含是否挂载 overlay）。
3. 读 `references/design.md`，严格按其骨架执行；按画像选 `templates/design-{backend,frontend,generic}.md` 并裁剪。
4. 用户输入 `$ARGUMENTS` 作为需求描述、澄清产物路径，或数字前缀（如 `00`，选中 `01-prd/00-*.md`）。
5. 产物写入 `.sdlc/02-design/00-<需求名>.md`（`<需求名>` 沿用 PRD 的需求名，勿用 `design` 等阶段通用词；命名规约见 skill）。

> 本命令是薄封装：设计逻辑、模板、绘图规范、overlay 叠加规则均以 `sdlc` skill 为**单一来源**，此文件不重复维护，也不硬编码任何模板绝对路径。
