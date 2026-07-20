# 阶段：方案设计（design）

产出一份结构化的技术设计文档。核心要求：**基于对现有代码的真实理解**做设计，而不是凭空想象；并按项目画像选对模板、裁掉不适用的章节。

## 输入

- `.sdlc/00-clarify/00-requirements.md`（澄清产物，首选），或
- 用户直接给的需求描述 / PRD 链接。

## 前置检查

1. **探测项目画像**：先读 `references/profiles.md` 跑探测，得出 profile 和启用的章节标签（tags）。向用户简报一行探测结论。
2. **选模板**：
   - `backend-service` → `templates/design-backend.md`
   - `web-frontend` → `templates/design-frontend.md`
   - `cli-library` / `oss-generic` → `templates/design-generic.md`
   - full-stack → backend + frontend 两份，或合并。
3. **缺澄清产物**时，若需求足够清晰可直接设计；若模糊，建议先跑 clarify，或就地做一轮精简澄清。

## 执行

**第一步：摸清现状（关键，别跳过）。** 设计要落在真实代码上：

- 用 codegraph（`codegraph_explore` 优先）或 grep 摸清相关模块、现有架构、命名与分层习惯。
- **找全引用**：涉及的接口/表/配置/缓存 key/消息，谁在用、改了会影响谁。这是评审阶段最常挂的地方，设计时就要查清。
- 复杂需求可派发 Explore 子 agent 并行调研多个子系统，避免主上下文被大量代码淹没。

**第二步：按裁剪后的模板填充。** 读选定的模板，只保留启用标签对应的章节：

- 未启用的标签章节（如未探测到 MQ 则去掉 `[mq]` 章节）直接不写进产出。
- `[enterprise-infra]` 默认剔除，用通用表述替代内部专有概念（映射见 `profiles.md` 第三节）。
- 每个保留的章节都要有实质内容——表格要填、流程要写清、异常分支要覆盖，不要留空表交差。

**绘图规范（重点：多图少文字）。** 设计文档以图为主、文字为辅——能用图讲清的逻辑就别写成大段文字。绘图遵循以下纪律：

- **图类型用 PlantUML**，以 ` ```plantuml ` 代码块内联进 Markdown（`@startuml...@enduml`）。架构/依赖用组件图，交互用时序图，业务逻辑用活动图，状态流转用状态图。每个核心流程、每处多服务交互、每个复杂状态机都应有对应的图。
- **图里不要放大段代码**。节点/参与者/动作用简洁的自然语言短语描述（如"校验库存"而非贴一段校验代码），逻辑清晰即可。图表达"谁和谁、按什么顺序、发生什么"，不表达"怎么用代码实现"。
- **画完必须校验语法**。每写完或改完一个 PlantUML 块，先抽出来过一遍校验，通过（退出码 0）再留在文档里。**务必带 `JAVA_TOOL_OPTIONS` 前缀走 headless 模式**，否则 macOS 上每次校验会弹出 Java 图形窗口：
  ```bash
  # 用 plantuml-lint skill 的校验脚本（退出码 0=通过 / 200=语法错误 / 1=环境问题）
  # JAVA_TOOL_OPTIONS 让 java 走无头模式，避免弹窗
  printf '<@startuml...@enduml 内容>' | JAVA_TOOL_OPTIONS=-Djava.awt.headless=true bash ~/.claude/skills/plantuml-lint/scripts/check.sh -
  # 或先写到临时文件再校验
  JAVA_TOOL_OPTIONS=-Djava.awt.headless=true bash ~/.claude/skills/plantuml-lint/scripts/check.sh /tmp/diagram.puml
  ```
  校验失败时按脚本报的行号定位修复，循环到退出码 0。写图前遇到不确定的语法，先查 `~/.claude/skills/plantuml-lint/references/diagram-types.md` 的对应图类型小节（含最小骨架与高频陷阱），避免反复报错。校验只抓语法错，逻辑（如 if 缺 endif）要自己再核一遍。
- 文字部分只承担图讲不清的：关键取舍的理由、约束条件、数值指标。

**第三步：自查设计完整性。** 交付前过一遍：正常流程 + 异常流程都设计了吗？兼容性/回滚考虑了吗？找全引用了吗？**每个核心流程/交互都配了 PlantUML 图且全部校验通过了吗？图里有没有混进大段代码？** **风险与权衡章节**是否诚实列出了关键取舍与遗留问题（不要留空——没有权衡的设计往往是没想透）？**验收标准回链章节**是否逐条对上了澄清阶段的验收标准、没有"未覆盖"的缺口？

## 产出

写入 `.sdlc/01-design/00-design.md`（多份时递增 `01-design-*.md`）。顶部元信息块：

```
> 需求名称：<name>
> 日期：<YYYY-MM-DD>
> 状态：待评审
> 关联：.sdlc/00-clarify/00-requirements.md
> 项目画像：<profile> ｜ 启用章节：<tags>
```

## 交接

展示产出路径 + 设计要点摘要（3–5 条）+ 找到的主要风险点。询问用户：

- 进入 **review** 阶段做设计评审（推荐——设计刚写完趁热评审）
- 还是先修改设计
- 或直接进入 code 阶段（跳过评审，适合简单改动）

进入 review 时，把本设计文档路径作为 review 的输入。
