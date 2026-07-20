# SDLC Skill 设计文档

> 版本：v0.1（设计稿，待评审）
> 日期：2026-07-17
> 定位：把重型 Python 编排引擎收敛为**一个纯提示词驱动的 Claude Code Skill**
> 状态：⏳ 待用户确认后落地

---

## 一、背景与目标

### 1.1 为什么要重做

现有 `sdlc` 是一个 Python CLI（13 包 + SQLite + 7 抽象 + 548 rules + LLM 抽象层）。实测结论：

- **能跑通的是 `/sdlc:*` slash 命令（Claude Code 编排）**：模板加载、文档产出、status 扫描都正常。
- **跑不通的是独立 `sdlc run` CLI**：temperature 硬编码、错误吞没、加载错包等根因链导致全流程 100% 失败（虽已修复但架构复杂度未降）。
- CLI 的 LLM 配置体系与 Claude Code 割裂（要单独配 API key，doctor 不检查）。

**核心判断**：真正为用户创造价值的是"提示词 + 模板 + checklist"这套编排知识，而不是承载它的 Python 引擎。引擎带来的 SQLite 状态机、Provider 抽象、Gate 同步阻塞等，都是可以由 Claude Code 本体能力（文件系统、子 agent、工具循环、上下文管理）天然覆盖的。

### 1.2 目标

设计一个**单一 SDLC skill**，满足：

1. **纯提示词实现**——没有任何需要安装/运行的二进制或 Python 包，全部逻辑用 Markdown 提示词表达。
2. **单一入口 + 子命令路由**——`/sdlc <阶段> [参数]`，一个 SKILL.md 分派到各阶段提示词。
3. **覆盖全生命周期**——澄清 → 设计 → 评审 → 编码 → 测试 → 上线，外加横切的 status。
4. **通用基座 + 自动裁剪**——内置通用模板，运行时探测技术栈/项目类型，自动裁剪不适用章节，消除旧版"企业企业内部专用"的适配噪音。
5. **渐进式披露**——SKILL.md 保持精简，各阶段提示词按需加载。

### 1.3 非目标（本次不做）

- ❌ 不迁移 SQLite 状态库、Provider 抽象、Gate 引擎、rule/gate/adapter YAML 体系。
- ❌ 不做企业规范 overlay（企业企业内部规范作为可选包，留待后续）。
- ❌ 不做团队协作、Web 审批、语义记忆、评估闭环（这些是产品级方向，非本 skill 范畴）。
- ❌ 不做代码级的自动编译/自动部署——编码/测试阶段借助 Claude Code 本体能力，不重造轮子。

---

## 二、设计原则

| 原则 | 含义 | 落地方式 |
| --- | --- | --- |
| **纯提示词** | 所有阶段逻辑是可读的 Markdown，无编译产物 | references/ 下每阶段一个 `.md` |
| **单一入口** | 用户只需记住 `/sdlc`，子命令分派 | SKILL.md 顶层做路由表 |
| **渐进式披露** | 不把全部阶段提示词一次性塞进上下文 | SKILL.md 只放路由 + 概览，阶段细节按需 Read |
| **通用优先** | 默认适配任意技术栈/项目类型 | 通用基座模板 + 探测式裁剪 |
| **状态即文件** | 阶段产物落到 `.sdlc/` 数字前缀阶段目录，段间靠读文件衔接 | 统一命名规约，无隐藏状态库 |
| **可跳段** | 支持从任意阶段进入（不强制走完整流程） | 每阶段独立可用，缺前置产物时询问 |
| **解释 why** | 提示词里说明为何这样做，而非堆 MUST | 遵循 skill-creator 写作规范 |

---

## 三、整体架构

### 3.1 目录结构

```
~/.claude/skills/sdlc/               # user-level skill
├── SKILL.md                         # 【入口】路由表 + 全生命周期概览 + 项目探测
├── references/                      # 【阶段提示词】按需加载
│   ├── clarify.md                   #   需求澄清
│   ├── design.md                    #   方案设计
│   ├── review.md                    #   设计评审
│   ├── code.md                      #   编码实现
│   ├── test.md                      #   测试
│   ├── deploy.md                    #   上线计划
│   ├── status.md                    #   状态查看
│   └── profiles.md                  #   项目画像探测 + 裁剪规则（被多个阶段引用）
└── templates/                       # 【产物模板】通用基座
    ├── design-backend.md            #   后端设计模板
    ├── design-frontend.md           #   前端设计模板
    ├── design-generic.md            #   通用/库/CLI 设计模板
    ├── review-report.md             #   评审报告模板
    ├── test-plan.md                 #   测试计划模板
    └── release-plan.md              #   上线计划模板
```

> 落地位置为 user-level（`~/.claude/skills/sdlc/`），因为它是跨项目通用的工作流工具。若某团队要项目内定制，可拷贝到 `<project>/.claude/skills/sdlc/`（project-level 优先级更高）。

### 3.2 三层加载模型（对应 skill-creator 的 progressive disclosure）

```
Level 1  Metadata (name+description)        始终在上下文  ~100 词
Level 2  SKILL.md body                      触发时加载    < 250 行（路由+概览+探测）
Level 3  references/*.md + templates/*.md   按需 Read     每阶段独立
```

关键：**SKILL.md 不内联各阶段的完整提示词**，只保留"这个子命令 → Read 哪个文件"的映射。这样 6 个阶段的细节不会同时占用上下文。

---

## 四、命令路由设计

### 4.1 调用形态

两种等价入口，都由同一个 SKILL.md 处理：

```
/sdlc clarify  <需求描述 | PRD 链接>
/sdlc design   <需求描述 | 澄清产物路径 | PRD 链接>
/sdlc review   <设计文档路径>
/sdlc code     <设计文档路径 | 开发单元>
/sdlc test     <代码范围 | 设计文档路径>
/sdlc deploy   <设计文档路径 | 变更说明>
/sdlc status   [design|review|deploy|...]
/sdlc          <自然语言需求>          # 无子命令 → 自动判断阶段或走引导
```

也支持自然语言（"帮我把这个需求做个设计"→ 等价 `/sdlc design`）。

### 4.2 SKILL.md 里的路由表（伪逻辑）

```
读取用户输入的第一个 token：
  clarify → Read references/clarify.md，按其执行
  design  → Read references/design.md
  review  → Read references/review.md
  code    → Read references/code.md
  test    → Read references/test.md
  deploy  → Read references/deploy.md
  status  → Read references/status.md
  其它/为空 → 进入"阶段推断"：
     - 含"澄清/不清楚/需求是否" → clarify
     - 含"设计/方案/架构"       → design
     - 含"评审/review/检查"     → review
     - 含"写代码/实现/开发"     → code
     - 含"测试/用例/覆盖"       → test
     - 含"上线/发布/部署/回滚"  → deploy
     - 含"进度/状态/有哪些文档" → status
     - 都不匹配 → 展示可用子命令，请用户选择
```

路由命中后，**第一步永远是先读 `references/profiles.md` 做项目探测**（见第六章），再进入具体阶段。

---

## 五、全生命周期阶段设计

每个阶段提示词遵循统一骨架：**输入 → 前置检查 → 执行职责 → 产出 → 交接**。

### 5.1 阶段总览

| 阶段 | 子命令 | 输入 | 产出（写入 `.sdlc/`） | 借用的 Claude Code 能力 |
| --- | --- | --- | --- | --- |
| 需求澄清 | `clarify` | 需求描述/PRD | `00-clarify/00-requirements.md` | document-reader 读 PRD、追问用户 |
| 方案设计 | `design` | 澄清产物/需求 | `01-design/00-design.md` | codegraph/grep 摸清现有代码、Explore 子 agent |
| 设计评审 | `review` | 设计文档 | `02-review/00-review.md` | 逐维度 checklist 核对 |
| 编码实现 | `code` | 设计文档 | 代码变更 + `03-code/00-impl-notes.md`（可选） | Edit/Write、code-review skill、run/verify skill |
| 测试 | `test` | 代码/设计 | `04-test/00-test-plan.md` + 测试代码 | 跑测试、覆盖率 |
| 上线计划 | `deploy` | 设计/变更 | `05-deploy/00-release-plan.md` | git diff 分析变更范围 |
| 状态查看 | `status` | — | 只读扫描汇总 | find/glob |

### 5.2 各阶段职责要点

**clarify（需求澄清）**
- 识别需求中的模糊点、边界、非功能约束（性能/安全/兼容）。
- 生成"澄清问题清单"，逐条追问用户；用户回答后固化为结构化需求规格。
- 若给了 PRD 链接（internal-docs/internal-docs），用 `document-reader` 读取。
- 产出：功能规格清单（含验收标准），供 design 阶段消费。

**design（方案设计）**
- 先探测项目画像 → 选择 `design-backend / design-frontend / design-generic` 模板并裁剪。
- 用 codegraph / grep 摸清现有架构、找全引用（接口/表/配置/MQ），避免拍脑袋设计。
- 复杂需求可派发 Explore 子 agent 并行调研多个子系统。
- 产出：按裁剪后模板填充的设计文档。

**review（设计评审）**
- 按裁剪后的 checklist 逐维度核对，每项给 Pass ✅ / Warning ⚠️ / Block ❌。
- 维度：架构完整性、数据/接口设计、核心流程与降级、缓存、异步/MQ、监控、灰度/回滚、容量、引用完整性——**其中企业内部专有维度按项目画像自动剔除**。
- 产出：结构化评审报告 + 风险分级（P0-P3）+ 改进建议 + 评审结论。

**code（编码实现）**
- 读设计文档，拆解为开发单元，逐单元实现（这是 Claude Code 的强项，skill 只负责编排与规范注入）。
- 每个单元完成后建议调用 `code-review` / `verify` skill 做自检。
- 产出：代码变更；可选的实现说明。

**test（测试）**
- 依据设计的验收标准与代码变更范围，生成测试计划 + 补齐测试代码，跑测试看结果。
- 产出：测试计划文档 + 测试代码 + 运行结果摘要。

**deploy（上线计划）**
- 分析 git diff 确定变更范围，梳理配置修改、SQL 调整、上线/回滚步骤、上线后检查清单。
- 检查清单同样按项目画像裁剪（非 JVM/非企业栈剔除对应项）。
- 产出：上线计划文档。

**status（状态查看）**
- 扫描 `.sdlc/` 下 `00-clarify/ ~ 05-deploy/` 各阶段目录，按数字前缀顺序输出各阶段产物清单与推断状态（待评审/已评审/已上线）。

---

## 六、项目画像与自动裁剪（核心改进）

这是相对旧版最重要的升级，直接解决"企业企业内部专用、通用项目大量填不涉及"的痛点。

### 6.1 探测（references/profiles.md 承载）

skill 每次进入实质阶段前，先做一次轻量探测：

| 信号文件 | 推断 |
| --- | --- |
| `pom.xml` / `build.gradle` | JVM 后端服务 |
| `package.json` (+ react/vue/next) | 前端 SPA / Node 服务 |
| `go.mod` | Go 服务 |
| `requirements.txt` / `pyproject.toml` | Python 服务/库 |
| `Cargo.toml` | Rust |
| 无 Web 框架、有 `main`/CLI 入口 | CLI 工具/库 |
| `.github/`、开源 LICENSE、无内部依赖 | 开源项目 |

综合得到**项目画像（profile）**，取值示例：`backend-service` / `web-frontend` / `cli-library` / `oss-generic`。探测不确定时直接问用户一句。

### 6.2 裁剪规则

模板与 checklist 采用**"通用基座 + 条件章节"**结构。每个可能不适用的章节打标签，探测结果决定去留：

```
章节标签           启用条件
[db]               探测到 ORM/SQL 依赖 或 用户确认涉及数据库
[cache]            探测到 redis 客户端 或 用户确认
[mq]               探测到 kafka/rabbit/pulsar 客户端 或 用户确认
[enterprise-infra] 仅当挂载企业 overlay（默认关闭）→ internal-sql-checker/internal-monitoring/internal-rpc/Apollo 等
[frontend-compat]  画像含前端
[jvm-runtime]      画像=JVM → JVM 内存/GC 类检查项
```

**裁剪动作**：不适用的章节直接不出现在产出里（而非留一堆"不涉及"占位），把"适用范围"说明保留在提示词里供 Claude 判断，产出保持干净。

### 6.3 通用化取舍对照（相对旧模板）

| 旧模板中的企业企业专有项 | 新处理方式 |
| --- | --- |
| internal-sql-checker SQL 校验 | 泛化为"SQL 经语法/规范校验（如 sqlfluff 或团队工具）" |
| internal-monitoring 存活/异常监控 | 泛化为"健康探针 / 错误率 / P99 延迟" |
| internal-rpc 实例数、internal-mq 消费 | 泛化为"实例数 / 消息队列消费（如涉及）"，[jvm]/[mq] 标签控制 |
| Apollo 动态配置 | 泛化为"配置中心（Apollo/Nacos/云配置）" |
| internal-gateway、城市配置后台、配送主流程 | 归入 [enterprise-infra]，默认剔除 |
| BI/数仓影响 | 归入 [enterprise-infra]，默认剔除 |

---

## 七、模板体系

### 7.1 模板清单与基座内容

- **design-backend.md**：需求描述 / 架构 / 数据库[db] / 接口 / 核心流程与降级 / 缓存[cache] / 异步消息[mq] / 监控 / 灰度回滚 / 容量 / 引用梳理。企业内部维度[enterprise-infra] 默认不渲染。
- **design-frontend.md**：需求 / 页面与路由 / 组件拆分 / 状态管理 / 接口契约 / 兼容性（浏览器/端）[frontend-compat] / 埋点 / 性能预算 / 灰度回滚。
- **design-generic.md**：需求 / 模块划分 / 公共 API 契约 / 数据结构 / 错误处理 / 兼容性 / 发布方式。用于库/CLI/工具类。
- **review-report.md**：评审摘要（总项/Pass/Warning/Block）+ 逐维度表 + 风险分级 + 改进建议 + 结论。
- **test-plan.md**：测试范围 / 用例矩阵（正常+边界+异常）/ 覆盖目标 / 运行结果。
- **release-plan.md**：上线主题 / 配置修改 / SQL 调整 / 上线步骤（含回滚）/ 监控指标 / 上线后检查清单。

### 7.2 与旧模板的关系

旧 `backend-design.md` / `release-checklist.md` 已做过一轮通用化（加了"适用范围"说明），本设计在此基础上：**把"适用范围文字提示"升级为"标签化条件章节 + 探测驱动裁剪"**，让通用项目拿到的产出真正干净，而不是自己去删"不涉及"的行。

---

## 八、状态与阶段衔接

### 8.1 产物目录与命名规约（`.sdlc/`，status 可扫描）

产物统一落到项目根的 `.sdlc/` 目录下，**每个阶段一个数字前缀文件夹**，文件夹内产物文件同样数字前缀（同一阶段多份产物时递增 00/01/02）：

```
.sdlc/
├── 00-clarify/
│   └── 00-requirements.md
├── 01-design/
│   └── 00-design.md
├── 02-review/
│   └── 00-review.md
├── 03-code/
│   └── 00-impl-notes.md        # 可选；代码变更本身在源码树
├── 04-test/
│   └── 00-test-plan.md
└── 05-deploy/
    └── 00-release-plan.md
```

- **数字前缀 = 阶段执行顺序**，天然按生命周期排序，`ls .sdlc/` 一眼看清进度到哪一步。
- 同一阶段产出多份文档时（如设计拆成 backend/db/frontend），文件名递增：`00-design.md`、`01-design-db.md`。
- 每份文件顶部保留元信息块（需求名 / 日期 / 状态 / 关联产物路径），形成弱链条。
- 多需求并行时，在 `.sdlc/` 下再分需求目录：`.sdlc/<slug>/00-clarify/...`（默认单需求可省略这一层）。

> 与旧 CLI 的运行时文件（`.sdlc/state.db`、`.sdlc/audit.jsonl`、`.sdlc/config.yaml`）可共存——数字前缀阶段文件夹与它们互不冲突，本 skill 也不读写那些文件。

### 8.2 段间传递

- 无隐藏状态库。下一阶段通过**读上一阶段的产物文件**获得上下文。
- 每份产物顶部带元信息块（需求名/日期/状态/关联文档路径），形成弱链条。
- 支持跳段：`/sdlc review .sdlc/01-design/00-design.md` 可直接评审，无需先跑 clarify/design。缺前置产物时，阶段提示词负责询问补齐。

### 8.3 与 Claude Code 原生能力的边界

| 旧引擎能力 | 新方案由谁承担 |
| --- | --- |
| SQLite 状态机 / resume | `.sdlc/` 阶段产物文件 + 会话上下文；长会话由 harness 自动压缩续接 |
| Subagent Pool / tool-loop | Claude Code 原生子 agent（Explore/general-purpose） |
| Gate 同步阻塞审批 | 阶段末尾向用户确认（继续/修改/跳过） |
| LLM Provider 抽象 | Claude Code 本体，无需单独配 key |
| rule/gate/adapter YAML | 提示词内联的 checklist + 探测裁剪 |
| 审计 JSONL | git 历史 + docs 产物 |

---

## 九、SKILL.md 骨架草稿

```markdown
---
name: sdlc
description: 全流程软件研发编排——用提示词驱动需求澄清、方案设计、设计评审、
  编码、测试、上线计划。当用户要"做设计文档 / 评审设计 / 出上线计划 / 澄清需求 /
  按研发流程推进一个需求"，或输入 /sdlc、/sdlc design、/sdlc review、/sdlc deploy
  等子命令时使用。自动探测项目技术栈并裁剪不适用的检查项，通用于后端/前端/CLI/开源项目。
---

# SDLC 研发流程编排

你是一个覆盖软件研发全生命周期的编排助手。用户通过 `/sdlc <阶段>` 或自然语言
驱动你在某个阶段工作。

## 第一步：解析子命令（路由）
[路由表：clarify/design/review/code/test/deploy/status → Read 对应 references 文件；
 无子命令时按关键词推断阶段]

## 第二步：探测项目画像
进入任何实质阶段前，先 Read references/profiles.md，按其探测技术栈与项目类型，
据此决定后续模板/checklist 的章节裁剪。

## 第三步：执行阶段
Read 命中的 references/<阶段>.md，严格按其"输入→前置检查→执行→产出→交接"执行。
产出写入 .sdlc/ 对应数字前缀阶段目录，遵循命名规约。

## 全生命周期概览
[一张阶段流转图 + 各阶段一句话职责，帮助模型建立整体心智]

## 交互约定
- 每阶段结束展示进度与产物路径，询问：继续下一阶段 / 修改 / 跳过。
- 支持从任意阶段进入；缺前置产物时主动询问补齐。
```

（各 references/*.md 的完整提示词在落地阶段编写，此处仅定骨架。）

---

## 十、从旧系统的迁移与取舍

| 旧资产 | 处置 |
| --- | --- |
| `/sdlc:*` slash 命令（design/review/deploy/run/status） | **提炼进 references/**，去企业化 + 去硬编码绝对路径；run 拆为全生命周期编排 |
| `builtin/templates/*.md` | 迁入 `templates/`，升级为标签化条件章节 |
| Python CLI（13 包 + SQLite + LLM 层等） | **本 skill 不依赖**；是否保留独立 CLI 产品线由产品决策（见 memory） |
| rule/gate/adapter/profile YAML | 不迁移；能力用提示词内联 checklist + 探测裁剪替代 |
| 企业企业内部规范（internal-sql-checker/internal-monitoring/internal-rpc/Apollo/BI） | 归入未来可选 `overlays/my-enterprise/`，默认不加载 |

---

## 十一、落地计划（确认后执行）

1. 创建 `~/.claude/skills/sdlc/` 骨架（SKILL.md + references/ + templates/）。
2. 写 SKILL.md（路由 + 概览 + 探测入口）。
3. 写 references/profiles.md（探测 + 裁剪规则），这是被复用的基础件，先做。
4. 逐阶段写 references/{clarify,design,review,code,test,deploy,status}.md。
5. 迁移并通用化 templates/（在旧模板基础上做标签化）。
6. 用 1-2 个真实需求做 sanity check（一个后端服务 + 一个前端/开源项目，验证裁剪效果）。
7. 视情况把旧 `/sdlc:*` slash 命令改为薄封装转调本 skill，或直接废弃。

---

## 十二、待确认项（评审时请拍板）

1. **落地位置**：user-level（`~/.claude/skills/sdlc/`）还是 project-level？（默认建议 user-level）
2. **旧 slash 命令去留**：本 skill 上线后，`~/.claude/commands/sdlc/*.md` 是废弃、还是保留为转调入口？
3. **code/test 阶段深度**：是仅做"编排 + 规范注入 + 调 code-review/verify"，还是要沉淀更细的编码规范 checklist？
4. **企业 overlay 时机**：企业企业内部规范是本次就放一个默认关闭的 `overlays/`，还是完全留待后续？
5. **模板粒度**：design 模板按 backend/frontend/generic 三分是否够用，是否要再细分（如 data-pipeline、mobile）？
```
