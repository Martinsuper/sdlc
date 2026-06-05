# 11 - 落地路线图

## 一、目标

将本方案从"设计文档"推进到"团队日常使用"，分 3 个阶段共 **6 个月**完成。

## 二、阶段总览

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  阶段 1      │   │  阶段 2      │   │  阶段 3      │
│  试点验证    │ → │  团队推广    │ → │  全面覆盖    │
│  2 个月      │   │  2 个月      │   │  2 个月      │
│              │   │              │   │              │
│ • 选 1 条线  │   │ • 团队级     │   │ • 部门级     │
│ • 跑通闭环   │   │ • 多线并行   │   │ • 100% 需求  │
│ • 度量基线   │   │ • Prompt 库  │   │ • 自优化     │
└──────────────┘   └──────────────┘   └──────────────┘
```

## 三、阶段 1：试点验证（M1-M2）

### 3.1 目标

- 跑通 1 条业务线的完整 7 阶段闭环
- 建立基线度量
- 沉淀 Subagent prompt 与 Skill 模板

### 3.2 试点选择标准

| 维度 | 标准 |
|---|---|
| 业务复杂度 | 中（不能太简单，也不能太复杂） |
| 团队 | 1 个有 DongBoot 经验的 TL + 2-3 个工程师 |
| 需求 | 明确、稳定、可量化 |
| 上下游 | 影响面 ≤ 3 个系统 |
| 时间窗口 | 1-2 周可上线 |
| 风险等级 | 低（出问题影响可控） |

**推荐试点**：内部工具类需求（如运营后台、报表系统）。

### 3.3 任务清单（M1-M2）

#### M1（4 周）

- [ ] **W1**：完成 10 个 Subagent 的 System Prompt v0.1
- [ ] **W1**：准备试点工程（DongBoot 接入、依赖完整）
- [ ] **W2**：跑通 Stage 1-2 闭环（PRD → 设计）
- [ ] **W2**：Gate 1/2 评审流程演练
- [ ] **W3**：跑通 Stage 3（编码）
- [ ] **W3**：多 Agent 并行验证
- [ ] **W4**：跑通 Stage 4-5（CR + 测试）
- [ ] **W4**：建立基线度量

#### M2（4 周）

- [ ] **W5**：跑通 Stage 6-7（部署 + 监控）
- [ ] **W5**：完成 4 个 Gate 模板
- [ ] **W6**：试点项目全流程贯通
- [ ] **W6**：试点上线 + 灰度
- [ ] **W7**：监控盘 + Runbook 实战
- [ ] **W7**：Gate 4 流程演练
- [ ] **W8**：试点复盘
- [ ] **W8**：Subagent prompt 升级到 v0.2

### 3.4 阶段 1 度量

| 指标 | 目标值 | 度量方法 |
|---|---|---|
| 端到端时长 | ≤ 10 工作日 | 时间戳 |
| 人工 Gate 次数 | ≤ 4 | Gate 状态 |
| Stage 失败回退率 | ≤ 20% | meta.json |
| 试点功能生产事故 | 0 | 故障台账 |
| Subagent prompt 修复次数 | ≤ 3 | 版本记录 |

### 3.5 阶段 1 产出

- [ ] 10 个 Subagent v0.2
- [ ] 4 个 Gate 模板
- [ ] 试点项目完整产物
- [ ] 复盘报告
- [ ] 团队级 Prompt 库 v0.1

### 3.6 阶段 1 退出条件

✅ 进入阶段 2 需满足：
- 试点功能成功上线
- 人工 Gate 流畅（评审时间 ≤ SLA）
- 至少 1 个完整产物被采纳
- 团队对 Subagent 信任度 ≥ 60%（问卷）

## 四、阶段 2：团队推广（M3-M4）

### 4.1 目标

- 团队内 3-5 条业务线并行使用
- Subagent prompt 沉淀为 v1.0
- 建立 Prompt 库与规则库

### 4.2 任务清单

#### M3（4 周）

- [ ] **W9**：将 10 个 Subagent prompt 升级到 v1.0
- [ ] **W9**：建立 Prompt 库结构（按 Stage 分类）
- [ ] **W10**：选定 3-5 条新业务线
- [ ] **W10**：培训团队成员（4h 培训 + 1h 演练）
- [ ] **W11**：3-5 条业务线并行启动
- [ ] **W11**：建立日站会（5min 同步 Gate 状态）
- [ ] **W12**：并行项目跟踪
- [ ] **W12**：收集 prompt 改进点

#### M4（4 周）

- [ ] **W13**：建立 Prompt 贡献机制（PR 形式）
- [ ] **W13**：Subagent 版本管理（v1.0 → v1.1）
- [ ] **W14**：3-5 条业务线继续推进
- [ ] **W14**：CR 子任务拆分（Code Reviewer / Security Reviewer / Performance Reviewer）
- [ ] **W15**：监控大盘自动创建验证
- [ ] **W15**：Runbook 自动生成验证
- [ ] **W16**：阶段 2 复盘
- [ ] **W16**：Subagent prompt 升级到 v1.1

### 4.3 阶段 2 度量

| 指标 | 目标值 |
|---|---|
| 并行业务线数 | ≥ 3 |
| 单条业务线端到端时长 | ≤ 7 工作日（比 M1 提升 30%） |
| Subagent 复用率 | ≥ 70% |
| Prompt 库条目 | ≥ 30 |
| 人工 Gate 平均放行时间 | ≤ 6h（Gate 1/3/4） |
| 人工 Gate 平均放行时间 | ≤ 8h（Gate 2） |
| Gate 驳回率 | ≤ 30% |
| Gate 多轮率 | ≤ 15% |

### 4.4 阶段 2 退出条件

✅ 进入阶段 3 需满足：
- 团队 50% 工程师日常使用
- 3 条以上业务线成功上线
- 0 起 P0 故障
- Subagent prompt 稳定（每周修改 < 5%）

## 五、阶段 3：全面覆盖（M5-M6）

### 5.1 目标

- 部门内 100% 需求走 SDLC 流水线
- Subagent 自优化
- 度量体系完善

### 5.2 任务清单

#### M5（4 周）

- [ ] **W17**：扩展到所有业务线
- [ ] **W17**：按业务域拆分（电商 / 物流 / 金融）
- [ ] **W18**：建立 Subagent 自优化机制
  - 收集失败案例
  - 自动更新 prompt
  - A/B 验证
- [ ] **W19**：建立 SDLC 度量平台
  - 端到端时长
  - 失败率
  - 人工 Gate 时长
  - 事故率
- [ ] **W20**：跨团队 Subagent 共享

#### M6（4 周）

- [ ] **W21**：优化 10 个 Subagent 到 v2.0
- [ ] **W21**：引入 Agentic 优化（自决策）
- [ ] **W22**：建立 Subagent Marketplace（共享 Subagent）
- [ ] **W22**：接入公司级 Skill 平台
- [ ] **W23**：准备 6 个月总结报告
- [ ] **W24**：规划下一阶段（自演化）

### 5.3 阶段 3 度量

| 指标 | 目标值 |
|---|---|
| 业务线覆盖 | 100% |
| 端到端时长 | ≤ 5 工作日 |
| 事故率 | ≤ 0.5% |
| 工程师满意度 | ≥ 80% |
| Subagent 自优化频率 | 每周 1 次 |
| 跨团队复用 | ≥ 3 个团队 |

## 六、关键风险与应对

### 6.1 风险矩阵

| 风险 | 概率 | 影响 | 等级 | 应对 |
|---|---|---|---|---|
| AI 误判导致线上事故 | 中 | 高 | 高 | 强制人工 Gate + 灰度 |
| 团队抗拒 AI 编码 | 中 | 中 | 中 | 培训 + 利益引导 |
| Subagent 成本失控 | 低 | 中 | 中 | 用 Sonnet 为主，关键 Stage 用 Opus |
| 上下文溢出 | 高 | 中 | 中 | Subagent 隔离 + 限输入 |
| 监控误报/漏报 | 中 | 高 | 高 | Runbook 演练 + 季度回顾 |
| DongBoot 组件未识别 | 低 | 中 | 中 | 调用 DongBootIntegration 自检 |
| M2 升级失败 | 中 | 高 | 高 | 灰度 1 个月 + 监控 |

### 6.2 风险升级机制

- **Subagent 失败 ≥ 3 次**：升级到人工处理
- **Gate 驳回 ≥ 3 轮**：升级到 D 类
- **生产 P0 事故**：立即冻结流水线，事后复盘

## 七、组织与角色

### 7.1 角色

| 角色 | 责任 | 人数（建议） |
|---|---|---|
| **SDLC Owner** | 整体推进、Subagent 维护 | 1 |
| **PM 代理** | Gate 1 评审 | 1+（原 PM 兼任） |
| **架构师** | Gate 2 评审 | 1+ |
| **Tech Lead** | Gate 3 评审 | 1+ |
| **SRE** | Gate 4 评审、监控维护 | 1+ |
| **QA** | 协助测试 Subagent | 1+ |
| **Subagent 工程师** | 维护 prompt 与 Skill | 1-2 |

### 7.2 工作量估算

| 阶段 | 人月 |
|---|---|
| 阶段 1 | 4 人月 |
| 阶段 2 | 6 人月 |
| 阶段 3 | 8 人月 |
| **合计** | **18 人月** |

## 八、度量平台

### 8.1 必度量

| 指标 | 数据源 | 频率 |
|---|---|---|
| 端到端时长 | meta.json | 每周 |
| Stage 耗时 | meta.json | 每周 |
| 人工 Gate 放行时间 | meta.json | 每周 |
| 驳回率 | meta.json | 每周 |
| 多轮率 | meta.json | 每周 |
| Subagent 成功率 | Subagent 日志 | 每天 |
| 事故率 | 故障台账 | 每月 |
| 工程师满意度 | 问卷 | 每月 |

### 8.2 可视化

- 实时看板：Subagent 状态
- 周报：流水线吞吐
- 月报：质量趋势

## 九、持续优化机制

### 9.1 Subagent 自优化

```
收集失败案例
   ↓
分类（按 Stage、按错误类型）
   ↓
Root cause 分析
   ↓
更新 prompt
   ↓
A/B 测试（新旧版各跑 5 个特性）
   ↓
效果好 → 升级 Subagent 版本
```

### 9.2 Prompt 库管理

- **位置**：`~/.claude/rules/sdlc-prompts/`
- **结构**：
  ```
  sdlc-prompts/
  ├── stage1-requirements/
  ├── stage2-design/
  ├── stage3-coding/
  ├── stage4-review/
  ├── stage5-testing/
  ├── stage6-deploy/
  ├── stage7-monitor/
  └── changelog/
  ```
- **贡献**：通过 PR 形式，需 1 个 TL + 1 个 SDLC Owner review

### 9.3 知识沉淀

每次 SDLC 完成后，自动沉淀：
- 新的 ADR 模板
- 新的 CR 模式
- 新的 Runbook 章节
- 新的告警规则

## 十、推广到其他团队

### 10.1 推广条件

✅ 阶段 3 完成后可推广：
- 100% 业务线已用
- 0 起 P0 事故超过 2 个月
- 团队满意度 ≥ 80%

### 10.2 推广方式

1. 培训（4h）+ 演练（1h）
2. 提供 1v1 启动支持（2 周）
3. 建立 SDLC Office Hour（每周）
4. 共享 Subagent 仓库

### 10.3 推广节奏

- M7：1 个新团队
- M8：2 个新团队
- M9：4 个新团队
- M10：部门级全面覆盖

## 十一、ROI 估算

### 11.1 成本

- Subagent 工程师：18 人月 × ¥30k = ¥540k
- 培训：¥50k
- 工具/MCP：¥100k
- **合计**：¥690k

### 11.2 收益（年度）

- 人力节省：5 个工程师 × ¥300k = ¥1,500k
- 周期缩短：30% × 项目数 × ¥200k = ¥2,000k
- 事故减少：50% × 平均事故成本 ¥500k = ¥750k
- **合计**：¥4,250k

### 11.3 回收期

ROI = (¥4,250k - ¥690k) / ¥690k = **516%**
回收期：≈ 2 个月

## 十二、附录

### 12.1 配套资源

- [DongBoot 接入文档](https://dongboot.jd.com)
- [opencode 文档](https://opencode.ai)
- [claude code 文档](https://docs.anthropic.com/claude-code)
- [internal-docs SDLC 频道](https://internal-doc.example)

### 12.2 相关 Skill

- `DongBootIntegration`
- `DongLog` / `DongLogBizLogger`
- `DongDAL` / `DongES` / `DongCache` / `DongHttp`
- `DongLock` / `DongSequence` / `DongSchedule` / `DongThread`
- `internal-mq` / `internal-rpc` / `JIMDB`
- `DongMonitorDashboard`
- `DongBootHotswapTroubleshoot` / `DeployBizLogTroubleshoot`
- `UnitTest` / `R2UnitTest` / `R2UnitTestV2` / `R2ReplayUnitTest`
- `AutoRegression`
- `MultiSkillCoordination`

### 12.3 文档维护

- **Owner**：SDLC Owner
- **更新频率**：每 Sprint 一次
- **变更通知**：团队周会同步 + internal-docs 公告
- **版本管理**：Git 仓库（与代码同源）
