# 10. 运行示例 (v2.0)

> **10 个真实场景，展示从用户输入到完成的全流程**  
> 每个示例包含：用户输入、检测结果、Pipeline 执行、Gate 决策、最终产物

---

## 示例 1：Java/DongBoot 新功能

### 用户输入
```
"我想做一个新功能：用户登录后能查看自己的订单历史。
用 Java DongBoot，调用现有的 OrderService 查询订单。"
```

### 检测结果
```
EntryPoint: idea（"我想做"关键词）
Profile: new-feature（默认）
Adapter: dongboot（工程文件含 pom.xml + com.jd.dongboot.*）
```

### 构建的 Pipeline
```yaml
stages:
  - s-clarify
  - s-design
  - s-impl
  - s-unit
  - s-cr
  - s-pkg
  - s-deploy
  - s-mon
edges: 7 条线性边
gates:
  - gate-1 after s-clarify (PM, 4h)
  - gate-2 after s-design (架构师, 8h)
  - gate-3 after s-cr (TL, on_severity P1, 4h)
  - gate-4 after s-mon (SRE+QA, 4h)
budget: {max_minutes: 1440, max_cost_usd: 5.0}
```

### 执行过程

**Stage s-clarify (15min)**
- Subagent `requirements-analyst` (Sonnet) 跑
- 输入：用户输入 + repo_context
- 输出：
  - `prd.md`：含用户故事/验收/风险
  - `user_story.md`：As a 登录用户 / I want 查看我的订单 / So that ...
  - `acceptance.md`：Given 已登录 / When GET /api/orders/my / Then 返回 200 + 订单列表
- 触发 Gate-1，PM 在 IM 中收到待办

**Gate-1 (PM, 30min)**
- PM 审 checklist 5 项
- 通过 → 继续

**Stage s-design (60min)**
- Subagent `architect` (Opus) 跑
- 输出：
  - `design_doc.md`：含 8 章节
  - `api_contract.yaml`：OpenAPI 3.0
  - `db_schema.sql`：无需新表（复用 orders 表）
  - `sequence_diagram.puml`：登录态校验 → OrderController → OrderService → DB
  - `adr.md`：决定用现有 OrderService.getOrdersByUserId()，不复用 UserContext 而新增轻量包装
- 触发 Gate-2，架构师收到

**Gate-2 (架构师, 2h)**
- 审 6 项 checklist
- 通过 → 继续

**Stage s-impl (90min)**
- Subagent `coder-jvm-dongboot` (Sonnet) 跑
- 触发 `MultiSkillCoordination`：
  - DongLog（加 BizLogger 埋点）
  - DongThread（无新线程池）
  - DongDAL（用 JdbcTemplate 查询）
  - DongHttp（无新 HTTP）
- 输出：
  - `OrderHistoryController.java`（含 @sdlc-* 锚点）
  - `OrderHistoryService.java`
  - `OrderHistoryServiceTest.java`（测试骨架）
  - `dongboot_anchors.yaml`

**Stage s-unit (30min)**
- Subagent `tester-unit` (Sonnet) 跑
- 触发 `UnitTest` skill（用 DongMock）
- 输出：`unit_test_report.md`，覆盖率 85%

**Stage s-cr (30min)**
- Subagent `reviewer` (Opus) 跑
- 输出：`review_report.md`，1 个 P2-Major（缺少用户上下文注入）
- 触发 Gate-3（on_severity P1，没触发，因最高 P2）
- Gate-3 跳过（无 P1+）

**Stage s-pkg (15min)**
- `mvn -DskipTests package`
- 输出：`order-history-1.0.0.jar`
- `deploy_manifest.yaml`

**Stage s-deploy (30min)**
- 调 dongboothotserver `image_deploy_from_pod`
- 推 staging
- 输出：`deploy_record.md`

**Stage s-mon (45min)**
- Subagent `sre-writer-jvm-dongboot` 跑
- 触发 `DongMonitorDashboard` skill
- 输出：
  - `dashboard.json`（订单查询 QPS/错误率/P99）
  - `alert.yaml`（错误率 > 1% 告警）
  - `runbook.md`
  - `slo.yaml`（可用性 99.9%）
- 触发 Gate-4

**Gate-4 (SRE+QA, 1h)**
- SRE 通过，QA 通过
- 部署 prod（灰度 10% → 100%）

### 最终产物
```
prd/feat-20260605-001-order-history/
  meta.json
  pipeline.yaml
  audit.log
  artifacts/
    01-clarify-prd.md
    01-clarify-user_story.md
    01-clarify-acceptance.md
    02-design-design_doc.md
    02-design-api_contract.yaml
    02-design-db_schema.sql
    02-design-sequence_diagram.puml
    02-design-adr.md
    03-impl-OrderHistoryController.java
    03-impl-OrderHistoryService.java
    03-impl-OrderHistoryServiceTest.java
    03-impl-dongboot_anchors.yaml
    04-unit-unit_test_report.md
    05-cr-review_report.md
    06-pkg-order-history-1.0.0.jar
    06-pkg-deploy_manifest.yaml
    07-deploy-deploy_record.md
    08-mon-dashboard.json
    08-mon-alert.yaml
    08-mon-runbook.md
    08-mon-slo.yaml
  snapshots/
    after-stage-s-clarify/
    after-stage-s-design/
    ...
```

---

## 示例 2：Python/Flask Bug 修复

### 用户输入
```
"用户反馈：下单后有时候返回 500。错误日志：
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint
复现：连续点 2 次提交按钮。"
```

### 检测结果
```
EntryPoint: bug（"bug"+"复现"关键词）
Profile: bug-fix
Adapter: python-flask（自动检测）
```

### Pipeline
```yaml
stages: [s-diagnose, s-fix, s-test, s-cr, s-deploy]
gates: [gate-2 after s-fix, gate-3 after s-cr]
budget: {max_minutes: 480, max_cost_usd: 2.0}
```

### 执行过程

**Stage s-diagnose (20min)**
- Subagent `coder-python-flask` + `architect`
- 输出：`diagnose_report.md`：
  - 根因：缺少唯一性约束的 idempotency_key
  - 影响范围：所有 POST /api/orders
- 建议：在 Order 表加 idempotency_key 唯一索引 + 服务层去重

**Stage s-fix (40min)**
- Subagent `coder-python-flask` 跑
- 输出：
  - `order_routes.py`：加幂等键检查
  - `tests/test_idempotency.py`：复现用例
  - `migrations/001_add_idempotency_key.sql`

**Stage s-test (30min)**
- Subagent `tester-python`
- 输出：单元测试 + 集成测试全过

**Stage s-cr (20min)**
- Subagent `reviewer`
- 输出：P3-Minor（建议加 metric），无 P1+
- 跳过 Gate-3

**Stage s-deploy (15min)**
- `docker build + push` 到 staging
- 输出：`deploy_record.md`

### 最终产物
- 5 个 stage 全部完成
- 耗时 2.5h
- 成本 $1.2
- 跳过了 Gate-1、Gate-4（bug-fix 必跳）

---

## 示例 3：紧急 Hotfix

### 用户输入
```
"线上 P0！订单服务 OOM，全部下单失败，影响 50w 用户。
oncall 已经在处理，需要快速止血 + 修因。"
```

### 检测结果
```
EntryPoint: hotfix（"P0"+"OOM"+"线上"）
Profile: hotfix
Adapter: dongboot（自动）
```

### Pipeline（精简）
```yaml
stages: [s-diagnose, s-fix, s-test, s-deploy, s-verify]
gates: [gate-3 after s-test]   # 仅 TL
budget: {max_minutes: 180, max_cost_usd: 1.5}
```

### 执行过程（180min 内）

**0-15min: s-diagnose（同时触发止血）**
- AI 自动建议："立刻 rollback 到 v2.3.1"
- oncall 收到 → 执行 rollback → 5min 内恢复
- AI 继续诊断：发现 v2.4.0 引入了未限流的 OrderExportJob，导致内存溢出

**15-90min: s-fix**
- Subagent coder-jvm-dongboot 跑
- 输出：
  - `OrderExportJob.java`：加分页 + 内存阈值
  - `OrderExportConfig.java`：限流配置
  - 锚点：@sdlc-hotfix 标记

**90-120min: s-test**
- 简版单测：复现 + 验证
- 不跑完整 R2（时间紧迫）

**120-150min: s-deploy**
- 走快速通道：image_deploy
- 灰度 1% → 10% → 50% → 100%（30min 内）

**150-180min: s-verify**
- 监控指标确认：内存稳定、订单成功
- 输出：incident 报告 + 5 Whys

**Gate-3 (TL)**
- 15min 内放行（紧急通道）

**Post-mortem (24h 内)**
- 必出
- 5 Whys + Action items
  - 短期：OrderExportJob 限流
  - 长期：所有批量任务强制走 DongSchedule + 资源限制

---

## 示例 4：Node/React 重构

### 用户输入
```
"把前端 UserProfile 组件从 class 改成 function component + hooks。
涉及 3 个文件，已用 jest 覆盖。"
```

### 检测结果
```
EntryPoint: refactor
Profile: refactor
Adapter: frontend-react
```

### Pipeline
```yaml
stages: [s-impact, s-design, s-refactor, s-unit, s-regression, s-cr, s-deploy]
gates: [gate-2 after s-design, gate-3 after s-cr]
budget: {max_minutes: 2880, max_cost_usd: 8.0}
```

### 关键 Stage
- **s-impact**：分析 3 个文件依赖、props/state、jest 用例覆盖
- **s-design**：输出 hook 拆分方案 + 状态管理决策
- **s-refactor**：用 coder-frontend-react 改写
- **s-regression**：跑 R2UnitTestV2 验证行为不变
- **s-cr**：reviewer 评审可读性

---

## 示例 5：监控新增

### 用户输入
```
"加个监控：订单创建错误率超 1% 告警，通知 oncall。"
```

### 检测结果
```
EntryPoint: monitor（"监控"+"告警"）
Profile: monitor-only
Adapter: dongboot
```

### Pipeline（最简）
```yaml
stages: [s-mon]
gates: [gate-4]
budget: {max_minutes: 60, max_cost_usd: 0.3}
```

### 产出
- `alert.yaml`：Prometheus 规则
- `runbook.md`：order_create_error_rate > 1% 排查步骤
- `dashboard.json`：Grafana panel

---

## 示例 6：MySQL → TiDB 迁移

### 用户输入
```
"把 OrderService 的数据库从 MySQL 迁到 TiDB。
涉及 5 张表，QPS 5000，需要双写 + 灰度。"
```

### 检测结果
```
EntryPoint: idea（"迁"+"涉及"）
Profile: migration（默认）
Adapter: dongboot
```

### Pipeline（最重）
```yaml
stages: [
  s-clarify, s-impact, s-design, s-impl, s-unit,
  s-integration, s-regression, s-cr, s-security-scan,
  s-pkg, s-deploy, s-verify
]
gates: [gate-1, gate-2, gate-3, gate-4]
budget: {max_minutes: 4320, max_cost_usd: 15.0}
canary_required: true
canary_duration_minutes: 1440  # 24h 灰度
```

### 关键 Stage
- **s-clarify**：产出迁移 PRD，含双写策略
- **s-impact**：分析 5 张表上下游、QPS、数据量
- **s-design**：迁移方案（Flyway 同步 + 双写 + 数据校验 + 灰度切读）
- **s-impl**：实现 DongDAL 数据源切换 + 双写 + 校验
- **s-verify**：双读对比、一致性检查、回滚演练

---

## 示例 7：代码评审（最简入口）

### 用户输入
```
"评审这段代码：
[paste code]"
```

### 检测结果
```
EntryPoint: code
Profile: review-only
Adapter: auto-detect
```

### Pipeline（1 个 stage）
```yaml
stages: [s-cr]
gates: []
budget: {max_minutes: 30, max_cost_usd: 0.2}
```

### 产出
- `review_report.md`：含 P0-P4 问题列表
- 5-10min 出报告

---

## 示例 8：测试补充

### 用户输入
```
"补 UserService 的单测，覆盖率目标 90%。"
```

### 检测结果
```
EntryPoint: test
Profile: test-only
Adapter: dongboot
```

### Pipeline
```yaml
stages: [s-unit, s-cr]
gates: [gate-3]
budget: {max_minutes: 240, max_cost_usd: 1.0}
```

---

## 示例 9：跨语言（前端 + 后端 + 移动端）协同

### 用户输入
```
"新增一个'分享到好友'功能：
- 后端加 /api/share 接口
- 前端加分享按钮（Web）
- 移动端加分享按钮（iOS/Android）"
```

### 检测结果
```
EntryPoint: idea
Profile: new-feature
Adapter: dongboot（backend）+ frontend-react（web）+ mobile-android + mobile-ios
```

### Pipeline（多 adapter）
```yaml
stages:
  - s-clarify
  - s-design
  - s-impl-backend        # adapter: dongboot
  - s-impl-frontend       # adapter: frontend-react
  - s-impl-mobile-android # adapter: mobile-android
  - s-impl-mobile-ios     # adapter: mobile-ios
  - s-unit                # 三端并行
  - s-integration
  - s-e2e
  - s-cr
  - s-pkg
  - s-deploy
  - s-mon
gates: [gate-1, gate-2, gate-3, gate-4]
```

### 关键变化
- 4 个 impl stage 并行（前端/移动端/backend）
- 多个 unit-test 阶段可并行
- e2e-test 跨平台
- 部署：3 个服务分别 deploy

---

## 示例 10：Resume

### 场景
```
昨天跑了 s-clarify + s-design，今天接着跑 s-impl。
```

### 用户输入
```
"继续 feat-20260605-001-order-history"
```

### 系统行为
1. 加载 meta.json + 最新 snapshot
2. 显示进度：
   ```
   feat-20260605-001-order-history
   ✅ s-clarify（PM 已通过）
   ✅ s-design（架构师已通过）
   ⏸ s-impl（implement-backend）— 等待启动
   ⏸ s-unit, s-cr, s-pkg, s-deploy, s-mon
   预算已用：15min / $0.10
   ```
3. 提示：
   - "继续"：从 s-impl 跑
   - "重跑 s-design"：从 s-design 跑
   - "修改 s-impl 的输入"：先编辑再跑

### Resume Token 验证
- 检查 token 未过期
- 校验产物 hash（防止外部修改）
- 校验 audit.log 完整性

---

## 总结

10 个示例覆盖：
- 3 个技术栈（Java/Python/Node-React）
- 4 种 Profile（new-feature/bug-fix/hotfix/refactor/migration/monitor/test/review）
- 3 种规模（1 stage / 8 stages / 12 stages）
- 3 种状态（新增/修复/重构）
- 1 个跨语言协同场景
- 1 个 Resume 场景

证明 v2.0 设计**可适配任意技术栈、任意项目类型、任意入口点**。
