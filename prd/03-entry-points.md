# 03. 入口点 (v2.0)

> **入口点 (EntryPoint) 回答"用户从哪个阶段进入工作流"**  
> 12 种 EntryPoint 覆盖绝大多数真实场景；用户不必"从 PRD 开始"

---

## 一、12 种 EntryPoint

| ID | 名称 | 用户典型输入 | 默认 Profile | 必跑 Stage |
|---|---|---|---|---|
| `idea` | 想法 | "我想做..." | new-feature | clarify → ... |
| `prd` | PRD | 贴 PRD / PRD 链接 | new-feature | clarify-validate → design → ... |
| `design` | 设计 | 贴 OpenAPI / 设计稿 | new-feature | design-validate → impl → ... |
| `code` | 代码 | 贴代码 / git diff | review-only | review → ... |
| `bug` | 缺陷 | "有个 bug" | bug-fix | diagnose → fix → ... |
| `refactor` | 重构 | "重构..." | refactor | impact → refactor → ... |
| `test` | 测试 | "写测试" | test-only | test → cr → ... |
| `review` | 评审 | "评审..." | review-only | cr |
| `deploy` | 部署 | "部署..." | deploy-only | package → deploy |
| `monitor` | 监控 | "加监控" | monitor-only | monitor-setup |
| `doc` | 文档 | "写文档" | docs-only | docs-update |
| `hotfix` | 紧急修复 | "线上 P0" | hotfix | diagnose → fix → test → deploy → verify |

---

## 二、每种 EntryPoint 详细规格

### 2.1 `idea` 想法

**用户典型输入**：
- "我想做一个新功能：[描述]"
- "我有个想法：[描述]"
- "能不能加个 [X]？"
- "需求是 [描述]，帮我评估"

**检测关键词**：
- 想做 / 想加 / 想增加 / 能不能 / 需求是 / 想法

**默认 Profile**：`new-feature`

**必跑 Stage**：`clarify → design → implement → test → cr → deploy → monitor`

**示例**：
```
用户: "我想做一个新功能：用户登录后能查看自己的订单历史"
→ EntryPoint: idea
→ Profile: new-feature
→ Adapter: 自动检测（基于工程文件）
→ Pipeline: clarify → design → implement-backend → unit-test → cr → package → deploy → monitor
→ Gate 1 在 clarify 后
```

### 2.2 `prd` PRD

**用户典型输入**：
- [贴 PRD markdown]
- https://example.com/prd/123
- "这是 PRD：[贴链接]"

**检测关键词**：
- PRD / 需求文档 / 产品需求
- 文件路径含 `prd`/`requirement`/`spec`

**检测结构**：
- 链接：匹配 `(http|https)://.*(prd|requirement|spec)/`
- 文件：扩展名 `.md` 且标题含 "PRD"/"需求"/"Requirement"
- 内容特征：含"用户故事"/"User Story"/"验收标准"/"Acceptance"

**默认 Profile**：`new-feature`

**必跑 Stage**：`clarify-validate → design → implement → ...`

**关键变更**：
- 跳过原始 clarify（已有 PRD），改为 `clarify-validate`（验证 PRD 完整性）
- 若 PRD 不完整，回退到 clarify

**示例**：
```
用户: [贴完整 PRD]
→ EntryPoint: prd
→ Pipeline: clarify-validate → design → ...
```

### 2.3 `design` 设计

**用户典型输入**：
- 贴 OpenAPI YAML
- 贴 Mermaid / PlantUML
- 贴架构图
- "这是接口设计：[OpenAPI]"
- "已经设计好了，帮我实现"

**检测关键词**：
- 设计 / 接口 / OpenAPI / Swagger / 架构

**检测结构**：
- OpenAPI: 文件以 `openapi:` 开头 或 扩展名 `.yaml` 含 `paths:`
- Mermaid: 含 `sequenceDiagram` / `flowchart` / `classDiagram`
- PlantUML: 含 `@startuml`

**默认 Profile**：`new-feature`

**必跑 Stage**：`design-validate → implement → ...`

### 2.4 `code` 代码

**用户典型输入**：
- 贴代码块
- git diff
- git branch name
- PR 链接
- "帮我看看这段代码"

**检测关键词**：
- 代码块（含 ``` 围栏）
- 包含 git/diff 字段
- PR/merge request 链接

**检测结构**：
- 围栏代码：匹配 ```\w+\n ... ```
- git diff: 含 `diff --git`
- PR 链接: `(http|https)://.*/(pull|merge)/(\d+)`

**默认 Profile**：`review-only`

**必跑 Stage**：`cr`

**示例**：
```
用户: [贴一段 Java 代码] "这段代码有什么问题？"
→ EntryPoint: code
→ Profile: review-only
→ Pipeline: cr
→ Subagent: reviewer (Opus, 只读)
```

### 2.5 `bug` 缺陷

**用户典型输入**：
- "有个 bug：[描述]"
- "用户反馈：[现象]"
- "测试发现：[问题]"
- "线上有问题（非 P0）"

**检测关键词**：
- bug / 缺陷 / 故障 / 问题（区分于 hotfix 的 P0/紧急）
- 报错 / 异常 / 不工作 / 失败

**默认 Profile**：`bug-fix`

**必跑 Stage**：`diagnose → fix → test → cr → deploy`

**关键约束**：
- 必先有 issue/JIRA 单号（强制）
- 必先 reproduce（测试用例复现）

### 2.6 `refactor` 重构

**用户典型输入**：
- "重构 [模块/类/函数]"
- "把 [A] 改成 [B] 风格"
- "优化 [代码]"
- "清理技术债"

**检测关键词**：
- 重构 / refactor / 重写 / 改造 / 优化（针对代码）/ 清理 / 技术债

**默认 Profile**：`refactor`

**必跑 Stage**：`impact-analysis → refactor → test → regression → cr → deploy`

**关键约束**：
- 行为不变（必须有完整测试覆盖）
- 必跑 regression（R2UnitTestV2 优先）

### 2.7 `test` 测试

**用户典型输入**：
- "帮我写测试"
- "补 [模块] 的单测"
- "覆盖率 [目标]"
- "补 [接口] 的集成测试"

**检测关键词**：
- 测试 / 单测 / 集成测试 / 覆盖率 / mock

**默认 Profile**：`test-only`

**必跑 Stage**：`test → cr`

### 2.8 `review` 评审

**用户典型输入**：
- "评审这个 PR：[链接]"
- "看看这个 MR：[链接]"
- "CR [模块]"

**检测关键词**：
- 评审 / review / CR / MR / PR

**默认 Profile**：`review-only`

**必跑 Stage**：`cr`

**注**：与 `code` 的区别
- `code`：用户贴代码本身
- `review`：用户贴 PR/MR 链接

### 2.9 `deploy` 部署

**用户典型输入**：
- "部署 [服务] 到 [环境]"
- "发版 [版本号]"
- "上 [staging/pre/prod]"

**检测关键词**：
- 部署 / 发版 / 发布 / 上线

**默认 Profile**：`deploy-only`

**必跑 Stage**：`package → deploy`

**环境校验**：
- prod 必走人工 Gate 4
- pre 强制 image_deploy

### 2.10 `monitor` 监控

**用户典型输入**：
- "加个监控"
- "订单创建错误率超 1% 告警"
- "配置 dashboard"
- "写个 runbook"

**检测关键词**：
- 监控 / 告警 / dashboard / runbook / 指标 / metric

**默认 Profile**：`monitor-only`

**必跑 Stage**：`monitor-setup`

**示例**：
```
用户: "订单创建错误率超 1% 告警"
→ EntryPoint: monitor
→ Pipeline: monitor-setup
→ 输出: alert rule + dashboard + runbook
```

### 2.11 `doc` 文档

**用户典型输入**：
- "写个 README"
- "更新 API 文档"
- "补 ADR"
- "写个 onboarding 文档"

**检测关键词**：
- 文档 / README / API 文档 / ADR / onboarding / 教程

**默认 Profile**：`docs-only`

**必跑 Stage**：`docs-update`

### 2.12 `hotfix` 紧急修复

**用户典型输入**：
- "线上 P0 故障"
- "生产环境 OOM"
- "数据库挂了"
- "接口全部超时"
- "立刻修，影响 [N] 万用户"

**检测关键词**：
- 紧急 / 立刻 / P0 / 故障 / 线上 / 生产
- OOM / 雪崩 / 不可用 / 全量超时

**默认 Profile**：`hotfix`

**必跑 Stage**：`diagnose → fix → test → deploy → verify`

**关键约束**：
- 跳过所有非必要 Gate
- 仅 Gate 3 (TL) 必走
- 全自动，3h 内完成
- 必须先有 incident 单
- 必带 post_mortem

---

## 三、EntryPoint 检测算法

### 3.1 主检测流程

```python
def detect_entrypoint(user_input: str, repo_context: dict) -> EntryPoint:
    # 1. 关键词检测（高优先级）
    keyword_match = keyword_detect(user_input, KEYWORD_RULES)  # 见 3.2
    if keyword_match and keyword_match.confidence > 0.9:
        return keyword_match.entrypoint
    
    # 2. 结构化检测
    if is_prd_link(user_input) or is_prd_file(user_input):
        return EntryPoint("prd")
    if is_openapi_yaml(user_input) or is_diagram(user_input):
        return EntryPoint("design")
    if has_code_block(user_input) and is_not_link(user_input):
        return EntryPoint("code")
    if is_pr_link(user_input):
        return EntryPoint("review")
    if is_git_diff(user_input):
        return EntryPoint("code")
    
    # 3. LLM 二次判定
    llm_result = llm_classify(user_input, REPO_CONTEXT, ALLOWED_ENTRYPOINTS)
    if llm_result.confidence > 0.7:
        return llm_result.entrypoint
    
    # 4. 模糊则询问用户
    candidates = keyword_match.candidates  # 前 3 个
    return ask_user_to_choose(candidates)
```

### 3.2 关键词规则（优先级从高到低）

```yaml
KEYWORD_RULES:
  hotfix:
    keywords: [紧急, 立刻, P0, 故障, 线上崩溃, 雪崩, OOM, 不可用, 全量超时]
    weight: 100
  bug:
    keywords: [bug, 缺陷, 报错, 异常, 失败, 不工作, 用户反馈]
    weight: 80
  refactor:
    keywords: [重构, refactor, 重写, 改造, 清理, 技术债]
    weight: 75
  monitor:
    keywords: [监控, 告警, dashboard, runbook, 指标, metric, SLO]
    weight: 70
  review:
    keywords: [评审, review, CR, MR, PR review, code review]
    weight: 65
  test:
    keywords: [写测试, 单测, 集成测试, 覆盖率, mock, 补测]
    weight: 60
  deploy:
    keywords: [部署, 发版, 发布, 上线, release, rollout]
    weight: 55
  doc:
    keywords: [文档, README, API 文档, ADR, onboarding, 教程]
    weight: 50
  design:
    keywords: [设计, 接口设计, OpenAPI, Swagger, 架构, 架构图]
    weight: 45
  prd:
    keywords: [PRD, 需求文档, 产品需求, requirement spec]
    weight: 40
  idea:
    keywords: [想做, 想加, 想增加, 能不能, 需求是, 想法]
    weight: 30
  code:
    # 没有显式关键词，靠结构化检测
    keywords: []
    weight: 0
```

### 3.3 模糊场景的处理

**歧义示例 1**：
- "线上有问题" → hotfix 还是 bug？
- **处理**：追问 "是否 P0/紧急？影响范围？"
  - 是 → hotfix
  - 否 → bug

**歧义示例 2**：
- "重构 X 顺便修个 bug" → refactor 还是 bug？
- **处理**：追问 "主要目标是？" + 严重度
  - 重构 + 小 bug → refactor
  - 修 bug + 小重构 → bug
  - 两个都重要 → 拆成两个 feature

**歧义示例 3**：
- "加个监控，顺便改个 bug" → monitor 还是 bug？
- **处理**：拆成两个 feature

---

## 四、EntryPoint 之间的转换

**场景**：跑着跑着发现需要换 EntryPoint

```
原 EntryPoint=review，发现有严重设计问题
→ 暂停当前 pipeline
→ 新建 EntryPoint=design 的子 pipeline
→ 完成后回到 review
```

**实现**：Pipeline 支持 `parent_pipeline_id` + `resume_from`

---

## 五、用户提示词模板

### 5.1 标准提示

```
你是 SDLC 编排者。

请识别以下输入属于哪种入口：
- idea: 模糊想法，从需求澄清开始
- prd: 已有 PRD
- design: 已有设计稿
- code: 已有代码（评审/重构）
- bug: 缺陷修复
- refactor: 重构
- test: 写测试
- review: 评审 PR
- deploy: 部署
- monitor: 加监控
- doc: 文档
- hotfix: 紧急修复

用户输入：
{user_input}

仓库上下文：
{repo_context}

返回 JSON：
{
  "entrypoint": "<id>",
  "confidence": <0-1>,
  "reasoning": "<为什么>"
}
```

### 5.2 二次确认提示

```
我识别这次任务为【{entrypoint}】，置信度 {confidence}。

如不准确请选择：
1. idea（模糊想法）
2. prd（已有 PRD）
3. design（已有设计）
4. code（评审/重构代码）
5. bug（缺陷）
6. refactor（重构）
7. test（写测试）
8. review（评审 PR）
9. deploy（部署）
10. monitor（加监控）
11. doc（文档）
12. hotfix（紧急修复）
```

---

## 六、EntryPoint 与 Profile 的对应

不是 1:1 强绑定。EntryPoint 是**用户意图**，Profile 是**项目类型**。

| 用户意图 | 默认 Profile | 常见替换 |
|---|---|---|
| idea | new-feature | poc（验证用） |
| prd | new-feature | migration（迁移项目） |
| bug | bug-fix | hotfix（P0 时） |
| refactor | refactor | - |
| hotfix | hotfix | - |
| review | review-only | security（安全敏感） |
| monitor | monitor-only | - |

用户可在对话中显式覆盖 Profile。

---

## 七、版本

- v2.0 (2026-06-05): 12 EntryPoint 库（取代 v1.0 的固定从 PRD 开始）
