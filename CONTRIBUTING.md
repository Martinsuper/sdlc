# 贡献指南

感谢你有兴趣为 `sdlc` 做贡献。本项目是一个兼容 **OpenCode 与 Claude Code 的 Agent Skill（纯提示词）**，没有需要编译的运行时代码——贡献即编辑提示词、模板与检查清单，并在真实项目中验证效果。

## 仓库结构

本仓库根即 skill 本体（`SKILL.md` 在根）：

```
.
├── SKILL.md              # 入口：子命令路由 + 全流程概览 + 语言约束
├── references/           # 各阶段提示词（init/clarify/design/review/code/test/deploy/status/archive/profiles）
├── commands/sdlc/        # OpenCode 与 Claude Code 共用的命令壳
├── scripts/              # 客户端同步脚本
├── templates/            # 产物模板（design-backend/frontend/generic、review-report、test-plan、release-plan）
├── overlays/             # 可选：企业内部规范 overlay（默认关闭）
└── roadmap/              # 产品规划文档（非 skill 运行时内容）
```

三层加载模型（progressive disclosure）：

- **Level 1** — `SKILL.md` frontmatter 的 `name` + `description`，始终在上下文。
- **Level 2** — `SKILL.md` 正文，触发时加载（路由 + 概览 + 探测入口）。
- **Level 3** — `references/*.md` 与 `templates/*.md`，各阶段按需 Read。

关键原则：**`SKILL.md` 不内联各阶段的完整提示词**，只保留"子命令 → 读哪个文件"的映射，避免所有阶段细节同时占用上下文。

## 本地验证

Skill 无运行时单测，需先做脚本静态检查和安装预览，再在真实项目里跑一遍：

```bash
bash -n scripts/*.sh
scripts/sync-opencode.sh --dry-run
```

重启 OpenCode 后，在样例项目中触发对应阶段（如 `/sdlc/design`、`/sdlc/review .sdlc/02-design/00-用户登录.md`），确认：

- 子命令路由到正确的 `references/<阶段>.md`。
- 项目画像探测正确，模板/checklist 裁剪符合预期（通用项目不应被迫填一堆"不涉及"）。
- 产物正确落到 `.sdlc/` 下的数字前缀阶段目录。
- 全程中文交互（见 `SKILL.md` 顶部语言约束）。

## 编辑约定

- **改阶段行为** → 编辑对应的 `references/<阶段>.md`，保持其内部的 **输入 → 前置检查 → 执行 → 产出 → 交接** 骨架。
- **改产物结构** → 编辑 `templates/` 下对应模板；可能不适用的章节要打标签（如 `[db]` `[cache]` `[mq]` `[enterprise-infra]`），由探测结果决定去留，而非留占位。
- **改路由或全流程约定** → 编辑 `SKILL.md`，同时确认子命令表与 `references/` 文件一一对应。
- **加企业专有规范** → 放到 `overlays/`，默认关闭，不污染通用基座。
- 提示词一律用中文书写；保持"多图少文字"，图用 PlantUML 并确保语法可通过 headless 校验。

## PR 流程

1. **Fork** 仓库，从 `main` 切出特性分支。
2. **修改**提示词/模板，commit message 说清改了哪个阶段、为什么。
3. **验证**：在真实项目跑一遍受影响的阶段，附上产物或截图作为证据。
4. **提交** PR，描述变更、关联 issue、贴出验证结果。
