# `sdlc` — 提示词驱动的全流程研发编排 Skill

> 用一个 Claude Code Skill 覆盖软件研发全生命周期——需求澄清、方案设计、设计评审、编码、测试、上线计划，产物即文件，不依赖任何独立引擎或外部服务。

**形态：** Claude Code Skill（纯提示词） · **交互语言：** 中文

---

## 这是什么

`sdlc` 是一个 Claude Code Skill。它把研发流程中真正有价值的部分——**编排逻辑 + 阶段模板 + 检查清单**——沉淀为提示词，由 Claude Code 本体能力（文件系统、子 agent、工具循环、上下文管理）驱动执行，不再需要单独的 Python CLI、SQLite 状态机或 LLM Provider 配置。

工作方式三条主线：

- **按阶段分工**：每个阶段有独立提示词文件（`references/<阶段>.md`），命中后再按需加载，避免一次性占满上下文。
- **通用优先**：进入实质阶段前先探测项目画像（后端服务 / 前端 SPA / CLI 库 / 开源项目），据此裁剪模板与检查清单中不适用的章节。
- **状态即文件**：所有产物落到项目根 `.sdlc/` 下的数字前缀阶段目录，段与段之间靠读上一阶段产物衔接，无隐藏状态库。

---

## 全生命周期

```
init  →  clarify → design → review → code → test → deploy
(前置)    (00)      (01)     (02)      (03)   (04)   (05)
准备      需求澄清   方案设计  设计评审   编码    测试   上线计划

               status —— 横切，任意时刻扫描进度
```

`init` 是前置准备（codegraph 初始化 + 文档合规整理），非产物阶段。之后流程**按序推进、前置门禁强制**：先有需求文档（PRD）→ 设计 → 评审**通过** → 编码 → 测试 → 上线 checklist；缺前置产物或评审未通过时默认不允许进入下一阶段（用户显式声明知风险可强制跳过）。

---

## 安装

本仓库即 sdlc skill 本体（`SKILL.md` 在仓库根）。跨项目通用，建议装到 user 级。

**方式一：软链接（推荐，本机开发用）**——工作区改动即时生效，无需重复同步，仓库是唯一来源：

```bash
# 在仓库根执行；软链用绝对路径，指向本仓库
ln -s "$PWD" ~/.claude/skills/sdlc
ln -s "$PWD/commands/sdlc" ~/.claude/commands/sdlc
```

**方式二：拷贝**——适合不需要跟随本仓库更新的机器：

```bash
cp -r . ~/.claude/skills/sdlc
mkdir -p ~/.claude/commands/sdlc && cp commands/sdlc/*.md ~/.claude/commands/sdlc/
```

**internal-client**——internal-client 不跟随符号链接,用同步脚本把 skill 拷过去(只同步 SKILL.md/references/overlays/templates,不带入仓库杂物),改动后需重启 internal-client:

```bash
scripts/sync-internal-client.sh            # 同步；--dry-run 可先预览
```

若某团队要项目内定制，拷贝到 `<project>/.claude/skills/sdlc/`（project 级优先级更高）。

---

## 用法

在 Claude Code 中通过 `sdlc <阶段>` 子命令或自然语言触发：

| 子命令 | 做什么 |
| --- | --- |
| `sdlc init`    | 前置准备：codegraph 初始化 + 文档合规检查 + 散落文档归位（先出方案再动手） |
| `sdlc clarify` | 需求澄清：识别模糊点、追问、固化功能规格 |
| `sdlc design`  | 方案设计：摸清现有代码，按裁剪后的模板产出设计 |
| `sdlc review`  | 设计评审：逐维度 checklist 核对，输出风险分级报告 |
| `sdlc code`    | 编码实现：拆解开发单元，逐单元实现并自检 |
| `sdlc test`    | 测试：生成测试计划 + 补齐测试代码 + 跑结果 |
| `sdlc deploy`  | 上线计划：变更范围、配置、回滚步骤、上线后检查清单 |
| `sdlc status`  | 状态查看：扫描 `.sdlc/` 汇总各阶段进度（只读） |
| `sdlc report`  | 项目/代码分析报告：现场扫描代码库做统计度量分析（结构/接口/依赖影响等），产出留档到 `.sdlc/<数字>-report/`（按需运行，独立于主流程） |

也可直接给自然语言需求（"帮我按研发流程做完这个需求"），Skill 会从 `clarify` 起逐阶段推进，每阶段结束与你确认再继续。流程按序推进、前置门禁强制：默认不允许跳过前置阶段（如未评审通过不得进入编码），仅在你显式声明知道风险时才放行。

---

## 产物目录

产物统一落到项目根 `.sdlc/`，每阶段一个数字前缀目录：

```
.sdlc/
├── 00-context/            # 上下文资料：架构文档、知识库等（非流程产物，供各阶段查阅）
├── 01-prd/00-用户登录.md      # 文件名用具体需求名，同一需求跨阶段沿用
├── 02-design/00-用户登录.md
├── 03-review/00-用户登录.md
├── 04-code/00-用户登录.md
├── 05-test/00-用户登录.md
└── 06-deploy/00-用户登录.md
```

`sdlc report` 另出分析报告到 `<数字>-report/`（目录数字接在流程产物之后，如 `07-report/00-结构分析.md`；独立于主流程、按需存在）。

---

## 仓库结构

本仓库根即 skill 本体：

```
.
├── SKILL.md              # 入口：子命令路由 + 全流程概览
├── references/           # 各阶段提示词（命中后按需加载）
├── commands/sdlc/        # 斜杠命令壳（薄封装，转调 skill 各阶段；装到 ~/.claude/commands/ 后可用 /sdlc:<阶段>）
├── templates/            # 产物模板（后端/前端/通用设计、评审、测试、上线）
├── overlays/             # 可选：企业内部规范 overlay（默认关闭）
└── roadmap/              # 产品规划文档（非 skill 运行时内容）
```

---

## License

MIT
