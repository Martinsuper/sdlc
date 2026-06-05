# 02. Stage 库 (v2.0)

> 18+ 标准 Stage，按 category 分类：**requirement / design / implement / test / review / deploy / operate / maintain**  
> 主流程 = 从 Stage 库中选取子集 → 拼装为 Pipeline DAG

---

## 一、Stage 库总览

| Category | Stage ID | 名称 | 默认 Subagent | 默认 Gate | 耗时 (min) |
|---|---|---|---|---|---|
| requirement | clarify | 需求澄清 | requirements-analyst | always | 15 |
| requirement | impact-analysis | 影响面分析 | architect | manual | 30 |
| design | design | 架构/详细设计 | architect | always | 60 |
| design | adr | 决策记录 | architect | never | 15 |
| implement | implement-backend | 后端编码 | coder-backend | never | 90 |
| implement | implement-frontend | 前端编码 | coder-frontend | never | 60 |
| implement | implement-mobile | 移动端编码 | coder-mobile | never | 90 |
| implement | implement-infra | 基础设施编码 | coder-infra | never | 60 |
| test | unit-test | 单元测试 | tester-unit | never | 30 |
| test | integration-test | 集成测试 | tester-integration | on_artifact_missing | 45 |
| test | regression | 回归测试 | tester-regression | manual | 60 |
| test | e2e-test | 端到端测试 | tester-e2e | manual | 90 |
| review | cr | Code Review | reviewer | on_severity(P1) | 30 |
| review | security-scan | 安全扫描 | security-scanner | always | 20 |
| deploy | package | 打包/构建 | deployer | never | 15 |
| deploy | deploy | 部署 | deployer | always | 30 |
| operate | monitor-setup | 监控/告警/Runbook | sre-writer | always | 45 |
| operate | incident-response | 故障响应 | sre-writer | always | 30 |
| maintain | refactor | 重构 | architect | manual | 120 |
| maintain | docs-update | 文档更新 | docs-writer | never | 20 |
| maintain | migration | 数据/服务迁移 | architect | always | 180 |
| maintain | rollback | 回滚 | deployer | always | 15 |

---

## 二、requirement 类

### 2.1 `clarify` 需求澄清

- **目的**：从用户模糊输入中提取结构化需求
- **输入**：`idea`（用户原始输入） / `prd`（如已有）/ 仓库上下文
- **输出**：`prd` / `user_story` / `acceptance` / `risk_register`
- **Gate**：always（4h, PM/BA）
- **Subagent**：`requirements-analyst` (Sonnet)
- **Skill 工具**：影响面分析、关键假设标注、PRD 模板

**输入 Schema**：
```yaml
inputs:
  - {artifact_type: idea, required: false}
  - {artifact_type: prd, required: false}
  - {artifact_type: repo_context, required: true, source: auto}  # 代码扫描
```

**输出 Schema**：
```yaml
outputs:
  - {artifact_type: prd, format: markdown}         # 若无 PRD 则生成
  - {artifact_type: user_story, format: markdown}  # 至少 1 个
  - {artifact_type: acceptance, format: markdown}  # 至少 1 个
  - {artifact_type: risk_register, format: markdown}  # 至少 1 条
```

**关键模板（PRD 必含章节）**：
1. 背景与目标（Why）
2. 用户故事（As a / I want / So that）
3. 功能需求（Must / Should / Could / Won't）
4. 非功能需求（性能/可用性/安全/合规）
5. 验收标准（Gherkin: Given/When/Then）
6. 风险与依赖
7. 范围边界（Out of scope）

### 2.2 `impact-analysis` 影响面分析

- **目的**：识别代码/数据/接口/上游/下游/团队的所有影响点
- **输入**：`prd` / `idea` / `user_story`
- **输出**：`impact_report`
- **Gate**：manual（高风险时）
- **Subagent**：`architect` (Opus)

**关键检查项**：
- 接口/Schema 变更
- 数据库 Schema 变更（DDL、DML）
- 上下游服务依赖
- 缓存/索引失效
- 团队/SLA/合规
- 数据迁移
- 回滚成本
- 性能与容量

---

## 三、design 类

### 3.1 `design` 架构/详细设计

- **目的**：从需求产出可实施的设计
- **输入**：`prd` / `impact_report` / 现有代码上下文
- **输出**：`design_doc` / `adr` / `api_contract` / `db_schema` / `sequence_diagram` / `risk_register`
- **Gate**：always（8h, 架构师/TL）
- **Subagent**：`architect` (Opus)
- **耗时**：60min（含外部依赖检查）

**design_doc 必含章节**：
1. 设计目标
2. 整体方案
3. 模块划分
4. 接口设计（API Contract / OpenAPI）
5. 数据模型（DB Schema / ER）
6. 关键流程（Sequence Diagram）
7. 异常处理
8. 性能与容量
9. 安全与合规
10. 风险与缓解

### 3.2 `adr` 决策记录

- **目的**：记录关键技术选型决策
- **输入**：`idea` / `design_doc`（部分决策）
- **输出**：`adr`
- **Gate**：never
- **Subagent**：`architect` (Opus)

**ADR 模板**：
```markdown
# ADR-{NNNN}: {决策标题}

## 状态
Proposed / Accepted / Deprecated / Superseded

## 背景
（为什么需要决策）

## 方案对比
| 方案 | 优点 | 缺点 | 成本 | 风险 |
|---|---|---|---|---|

## 决策
（选择哪个方案）

## 影响
（对系统/团队/未来的影响）

## 替代方案
（未来如需反转，可选的替代方案）
```

---

## 四、implement 类

### 4.1 `implement-backend` 后端编码

- **目的**：实现后端业务逻辑
- **输入**：`design_doc` / `api_contract` / `db_schema` / `sequence_diagram`
- **输出**：`code`（含 DongBoot 锚点 / OpenAPI stub）/ `db_schema_diff`（Flyway/Liquibase）
- **Gate**：never（CR 在 review 阶段）
- **Subagent**：`coder-backend` (Sonnet) 或 adapter 特定（`coder-jvm-dongboot` / `coder-python-flask` 等）
- **耗时**：90min

**强制产物**（来自 DongBoot 实战经验）：
- 业务方法必有 BizLogger 日志
- 强制使用 adapter 推荐的组件（cache/http/lock/log/threadpool/database）
- 锚点注释（按语言）
  - Java/DongBoot: `@sdlc-feature`, `@sdlc-stage`, `@sdlc-requirement`, `@sdlc-adr`, `@sdlc-generated-by`, `@sdlc-timestamp`
  - 其他语言：文件头注释同样字段
- 错误码规范（`{业务域}.{模块}.{错误码}`）
- 单元测试骨架（待 unit-test 阶段填充）

### 4.2 `implement-frontend` 前端编码

- 同上，输出含组件、Storybook、单元测试骨架
- **Subagent**：`coder-frontend` (Sonnet)

### 4.3 `implement-mobile` 移动端编码

- **Subagent**：`coder-mobile` (Sonnet)
- 输出：原生/跨端代码 + 平台特定 manifest

### 4.4 `implement-infra` 基础设施编码

- **Subagent**：`coder-infra` (Sonnet)
- 输出：Terraform / Helm Chart / Dockerfile / CI YAML
- 必含：环境差异（dev/staging/pre/prod）、密钥管理、IaC 校验

---

## 五、test 类

### 5.1 `unit-test` 单元测试

- **目的**：为实现代码写单元测试，覆盖率 ≥ 80%
- **输入**：`code` / `api_contract` / `db_schema`
- **输出**：`code`（测试文件） / `unit_test_report`
- **Gate**：never
- **Subagent**：`tester-unit` (Sonnet)
- **耗时**：30min
- **测试框架**（按 Adapter）：
  - Java/DongBoot: JUnit5 + DongMock DSL（mock().from + @MockMethod）
  - Python/Flask: pytest + unittest.mock
  - Node/Express: jest + supertest
  - Go/Gin: testing + testify

### 5.2 `integration-test` 集成测试

- **目的**：跨服务/数据库/中间件验证
- **输入**：`code` / `api_contract` / `db_schema` / 测试数据
- **输出**：`integration_test_report`
- **Gate**：on_artifact_missing
- **Subagent**：`tester-integration` (Sonnet)
- **耗时**：45min

### 5.3 `regression` 回归测试

- **目的**：基于 R2 录制 + 业务监控跑回归用例
- **输入**：`code` / R2 case 文件 / 接口契约
- **输出**：`regression_report` / R2 链接
- **Gate**：manual
- **Subagent**：`tester-regression` (Sonnet)
- **Skill 工具**：R2UnitTestV2（默认入口）/ R2UnitTest（兜底）/ R2ReplayUnitTest（专项）
- **耗时**：60min

### 5.4 `e2e-test` 端到端测试

- **目的**：用户视角的全链路验证
- **输入**：`code` / `user_story` / `acceptance`
- **输出**：`e2e_report`
- **Gate**：manual
- **Subagent**：`tester-e2e` (Sonnet)
- **工具**：Playwright / Cypress / Appium

---

## 六、review 类

### 6.1 `cr` Code Review

- **目的**：人工 + AI 评审代码质量与设计一致
- **输入**：`code` / `db_schema_diff` / `design_doc`
- **输出**：`review_report`
- **Gate**：on_severity(P1)（P0/P1 必走）
- **Subagent**：`reviewer` (Opus) — **只读**，无 write/edit 权限
- **耗时**：30min
- **评审维度**：
  - 正确性
  - 可读性 / 可维护性
  - 性能
  - 安全（OWASP Top 10）
  - 兼容性
  - 测试覆盖
  - 错误处理
  - 日志/可观测性
  - 文档/注释
  - 锚点规范

**严重度**：
- P0-Blocker：合并前必修
- P1-Critical：合并前修
- P2-Major：建议修
- P3-Minor：建议优化
- P4-Suggestion：可选

### 6.2 `security-scan` 安全扫描

- **目的**：自动化安全检查
- **输入**：`code` / `api_contract` / 依赖清单
- **输出**：`security_report`
- **Gate**：always（高风险 Profile 必走）
- **Subagent**：`security-scanner` (Sonnet)
- **工具**：SAST（SonarQube / Semgrep / CodeQL）/ 依赖扫描（OWASP Dependency-Check / Snyk）/ DAST（如适用）

---

## 七、deploy 类

### 7.1 `package` 打包/构建

- **目的**：编译/构建可部署产物
- **输入**：`code` / `config` / `deploy_manifest`
- **输出**：`deploy_manifest`（含镜像 tag / 版本号 / 环境变量）
- **Gate**：never
- **Subagent**：`deployer` (Sonnet)
- **工具**（按 Adapter）：
  - Java/DongBoot: `mvn -DskipTests package` → `target/*.jar`
  - Python: `python -m build` / Docker
  - Node: `npm run build` / Docker
  - Go: `go build` / Docker

### 7.2 `deploy` 部署

- **目的**：把产物推到目标环境
- **输入**：`deploy_manifest` / `config` / 当前环境
- **输出**：`deploy_record`
- **Gate**：always（4h, SRE/QA）
- **Subagent**：`deployer` (Sonnet)
- **环境策略**：
  - develop: hot_deploy / image_deploy（自由）
  - staging: image_deploy
  - pre: image_deploy 强制（不允许 hot_deploy）
  - prod: 强制人工，灰度 + 监控

**部署方式**（按 Adapter）：
- Java/DongBoot: 行云 image_deploy_from_pod / hot_deploy（仅 dev/staging）
- 容器化: kubectl apply / Helm install
- 静态: rsync / scp

---

## 八、operate 类

### 8.1 `monitor-setup` 监控/告警/Runbook

- **目的**：上线后配置监控、SLO、告警、Runbook
- **输入**：`deploy_record` / `api_contract` / `slo`（可空）
- **输出**：`dashboard` / `alert` / `runbook` / `slo` / `metric_definition`
- **Gate**：always（4h, SRE/QA）
- **Subagent**：`sre-writer` (Sonnet)
- **耗时**：45min
- **Skill 工具**（DongBoot 环境）：DongMonitorDashboard（业务监控盘全流程）

**必含**：
- 黄金信号（Latency / Traffic / Errors / Saturation）
- 业务关键指标（订单成功率、支付成功率等）
- 告警阈值（按 SLO 设定）
- Runbook（故障处理步骤）
- 值班 oncall 通知

### 8.2 `incident-response` 故障响应

- **目的**：线上故障时快速止血
- **输入**：`incident`（告警触发）/ `deploy_record`
- **输出**：`incident` / `post_mortem` / 修复 PR
- **Gate**：always
- **Subagent**：`sre-writer` (Sonnet)
- **动作**：
  1. 止血（rollback / feature flag / 限流）
  2. 定位（log / metric / trace）
  3. 修复（hotfix pipeline）
  4. 复盘（post-mortem，5 Whys）
  5. 预防（action items）

---

## 九、maintain 类

### 9.1 `refactor` 重构

- **目的**：在保持行为不变前提下改善代码结构
- **输入**：`code` / `impact_report` / 测试报告
- **输出**：`code` / `regression_report`
- **Gate**：manual
- **Subagent**：`architect` (Opus) + `coder-backend` (Sonnet)
- **耗时**：120min
- **必含**：完整回归测试 + 性能对比

### 9.2 `docs-update` 文档更新

- **目的**：README / API 文档 / Runbook / ADR 维护
- **输入**：`code` / `api_contract` / 变更说明
- **输出**：`docs`
- **Gate**：never
- **Subagent**：`docs-writer` (Sonnet)
- **耗时**：20min

### 9.3 `migration` 数据/服务迁移

- **目的**：把系统从 A 迁到 B（如 MySQL→TiDB、HTTP→gRPC）
- **输入**：`impact_report` / `migration_plan`
- **输出**：`migration_plan` / `code` / `deploy_record`
- **Gate**：always
- **Subagent**：`architect` (Opus) + `coder-backend` (Sonnet) + `deployer` (Sonnet)
- **耗时**：180min
- **必含**：双写 / 灰度 / 数据校验 / 回滚预案

### 9.4 `rollback` 回滚

- **目的**：把服务回退到上一个稳定版本
- **输入**：`deploy_record` / 目标版本
- **输出**：`deploy_record`（回滚后）
- **Gate**：always
- **Subagent**：`deployer` (Sonnet)
- **耗时**：15min
- **前置**：必须保留最近 N 个版本的镜像/包

---

## 十、Stage 的可配置项

每个 Stage 在 Pipeline 中可被覆盖：

```yaml
- instance_id: s-design-custom
  stage_id: design
  enabled: true
  subagent_override: architect-junior         # 用 junior 替代
  inputs_override: [prd, impact_report, security_baseline]  # 额外加安全基线
  outputs_override: [design_doc, adr, threat_model]  # 额外加威胁建模
  gate_override:
    trigger: always
    sla_hours: 24
    approvers: [{role: security, min_count: 1}]
  budget: {max_minutes: 180}
```

---

## 十一、Stage 选取算法（Pipeline Builder 的一部分）

```
build_stages(profile, entrypoint, user_overrides) → [stage_instance]
  1. 从 Profile 取 default_stages（必跑）
  2. 从 EntryPoint 取 default_stages（必跑）
  3. 从 user_overrides 取 enabled/disabled
  4. 从 Profile 取 skip_stages（必跳）
  5. 合并去重，得到 base_set
  6. 加上 user_overrides 强制加入的 stage
  7. 校验依赖（如 impl 必在 design 之后）
  8. 校验 Gate 触发条件（如 on_severity(P1) 需前一 stage 输出含 severity）
  9. 返回 stage_instance 列表
```

---

## 十二、版本

- v2.0 (2026-06-05): 18+ Stage 库（取代 v1.0 的 7 固定阶段）
- v2.1 (2026-06-05): 每个 stage 增加 `post_action: kb_update`（自动更新 KB，详见 `13-memory-and-evolution.md` §五）

---

## 十三、Stage 通用 post_action：KB 自动更新（v2.1 新增）

> 每个 stage 完成后，自动触发 KB 增量更新，让 SDLC 系统"越用越懂项目"。

### 13.1 通用 post_action 定义

```yaml
post_action:
  kb_update:
    enabled: true
    auto_generated: true       # 标记为自动生成
    human_review_required: false  # 默认不需要人审（高价值字段除外）
    rollback_supported: true   # 写错可回滚
```

### 13.2 Stage → KB 文件映射表

| Stage | 写哪些 KB 文件 | 写什么 | 触发条件 |
|---|---|---|---|
| `clarify` | `glossary.md`, `conventions.md`(待确认) | 新术语、新约定 | 提取出 ≥1 个新术语/约定 |
| `impact-analysis` | `components.md`, `antipatterns.md` | 受影响组件、潜在风险点 | 发现 ≥1 个高风险点 |
| `design` | `architecture.md`, `decisions.md` | 新架构、新 ADR | 完成设计输出 |
| `adr` | `decisions.md` | 新 ADR | always |
| `implement-*` | `components.md`, `patterns.md`, `antipatterns.md` | 新组件、新模式、新反模式 | 写代码时用到 |
| `unit-test` | `patterns.md`, `antipatterns.md` | 测试模式 | 完成单元测试 |
| `integration-test` | `runbook.md`(草稿) | 集成测试步骤 | always |
| `regression` | `antipatterns.md` | 回归发现的反模式 | 发现新反模式 |
| `e2e-test` | `runbook.md` | E2E 测试步骤 | always |
| `cr` | `antipatterns.md` | CR 发现的反模式 | CR 不通过 |
| `security-scan` | `antipatterns.md`, `runbook.md` | 安全反模式、修复步骤 | 发现安全问题 |
| `package` | (无) | - | - |
| `deploy` | `runbook.md` | 部署步骤、roll-back 步骤 | always |
| `monitor-setup` | `runbook.md`, `components.md` | runbook、新增监控 | always |
| `incident-response` | `lessons-learned.md` | 故障复盘 | 故障 P0/P1 |
| `refactor` | `patterns.md`, `architecture.md` | 重构模式 | always |
| `docs-update` | `glossary.md`, `architecture.md` | 文档同步 | always |
| `migration` | `runbook.md`, `patterns.md` | 迁移步骤、迁移模式 | always |
| `rollback` | `runbook.md`, `lessons-learned.md` | 回滚步骤、教训 | always |

### 13.3 KB 写入规则

1. **diff-only**：只写差异，不全量覆盖
2. **append-mode**：默认追加，人工编辑的段落不动
3. **fingerprint check**：写入前比对文件指纹，避免冲突覆盖
4. **async + batch**：KB 写入异步批量，不阻塞 stage 返回
5. **rollback window**：KB 写入 24h 内可回滚，超时需人审
6. **audit**：每次 KB 写入生成 `kb_updated` 事件到 `audit.log`
7. **conflict resolution**：Subagent 与人工编辑冲突时，**人工优先**（Subagent 写入失败，告警给 PM）

### 13.4 KB 写入 Schema（统一格式）

```yaml
kb_update_record:
  stage_id: string
  at: timestamp
  files_changed: [string]
  additions:
    components: [{name, version, role, evidence_file}?]
    patterns: [{name, code_template, when_to_use, evidence_file}?]
    antipatterns: [{name, bad_example, why_bad, fix, evidence_file}?]
    adrs: [{id, title, decision, consequences, date}?]
    runbooks: [{scenario, steps, owner, evidence_file}?]
    lessons: [{title, root_cause, fix, prevention, date}?]
  summary: string            # 一句话总结
  auto_generated: bool
  confidence: float          # 0.0-1.0，低于 0.6 标"待确认"
```

### 13.5 进化触发器（自动写 KB 的额外场景）

| 触发器 | 写 KB | 何时触发 |
|---|---|---|
| 同模式实现 ≥3 次 | `patterns.md`（抽象为新模式） | Subagent 自检 |
| CR 拒绝某类 ≥3 次 | `antipatterns.md`（加入新反模式） | reviewer 自检 |
| Pipeline 失败 ≥2 次同根因 | `lessons-learned.md` | pipeline_runner 自检 |
| 线上事故 P0/P1 | `lessons-learned.md`（postmortem） | sre-writer |
| Subagent 重复纠正 | `conventions.md` | meta 学习 |

### 13.6 Subagent 必带的 KB 上下文（注入）

每个 Subagent 启动时，自动注入（按相关性排序）：

```yaml
subagent_context_injection:
  required:
    - architecture.md         # 全文
    - conventions.md          # 全文
    - patterns.md             # top-10 最相关
    - antipatterns.md         # top-10 最相关
  optional:
    - components.md           # 按当前 stage 涉及到的组件过滤
    - decisions.md            # 按 tag 过滤
    - runbook.md              # 按 scenario 过滤
    - lessons-learned.md      # 按 root_cause 过滤
  budget:
    max_tokens: 4000          # 控制注入量
    strategy: relevance_sort  # 相似度排序
```

详见 `13-memory-and-evolution.md` §六。
