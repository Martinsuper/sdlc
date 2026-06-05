# 12. 实施路线图 (v2.1)

> **8 个月分 4 阶段，每阶段 2 个月**  
> 从「可跑通新功能」到「记忆/KB 系统」到「全 adapter 全 Profile 覆盖」到「企业级落地」

---

## 一、阶段总览

```
Phase 1 (M1-M2): MVP - 单 adapter (dongboot) + 核心 4 Profile
Phase 2 (M3-M4): 记忆 - 3 层 KB + sdlc init + 上下文自动更新 + Subagent 自适应
Phase 3 (M5-M6): 扩展 - 5 个主流 adapter + 10 Profile + Skill 协同完善
Phase 4 (M7-M8): 完善 - 全部 18 adapter + 14 Profile + 企业治理 + 商业化
```

| 阶段 | 周期 | 目标 | 关键指标 |
|------|------|------|----------|
| **P1 MVP** | M1-M2 | 跑通 dongboot 全流程 1 个完整需求 | 1 团队能用、覆盖 4 Profile |
| **P2 记忆** | M3-M4 | 3 层 KB + sdlc init + 越用越好用 | 1 团队能 init + KB 自动更新、复用率 > 50% |
| **P3 扩展** | M5-M6 | 5 个 adapter、10 Profile、Skill 完善 | 5 个团队能用、Pipeline 复用率 > 70% |
| **P4 完善** | M7-M8 | 全 adapter 全 Profile + 治理 + 商业化 | 全公司推广、产出可商业化产品 |

---

## 二、Phase 1: MVP（M1-M2）

### M1：基础能力 + dongboot adapter

#### Week 1: 脚手架
- 工程初始化（CLI 工具 + 配置中心 + 注册表）
- 文档 0-12 + 14（基础机制 + Subagent 池 + init）
- `~/.claude/stages/` 目录 + 6 个 stage YAML
- `~/.claude/agents/agents.yaml` + 5 个通用 Subagent

#### Week 2: 核心机制
- Pipeline Builder 算法实现
- EntryPoint 检测（12 种）
- Project Profile 引擎（4 个核心 Profile）
- Adapter 检测 + dongboot adapter 完整实现
- Stage Runner + 状态机

#### Week 3: 集成 dongboot
- dongboot adapter 完整实现（18+ 组件映射）
- 编码锚点规范强制（`@sdlc-*` 5 个）
- Subagent coder-jvm-dongboot 注册
- 调 MultiSkillCoordination + DongLog + DongDAL + DongThread

#### Week 4: 闭环
- Gate 机制（4 个 Gate + 6 个扩展）
- Audit log + snapshot
- Resume 机制
- **1 个真实需求端到端跑通**（例：订单查询接口）

### M2：跑通 + 4 Profile

#### Week 5: 3 个新 Profile
- bug-fix：diagnose + fix + test + cr + deploy
- hotfix：紧急通道 + 简化 Gate + 180min 内闭环
- refactor：impact-analysis + 设计 + 行为不变验证

#### Week 6: 测试与监控
- UnitTest skill 集成（带 DongMock）
- R2UnitTestV2 集成（默认）+ R2UnitTest 兜底
- AutoRegression skill 集成
- DongMonitorDashboard skill 集成

#### Week 7: 部署与运维
- DongBootHotswapTroubleshoot + DeployBizLogTroubleshoot
- 部署策略：dev/staging 允许 hot_deploy 或 image_deploy，pre 强制 image_deploy
- 灰度发布 + rollback

#### Week 8: 完善 + 灰度
- 文档 9-12 完成
- CLI 工具（`sdlc run / status / resume / trace`）
- 1 个团队试运行（5 人）
- 收集反馈、修 20+ bug

### P1 验收标准
- [ ] 1 个 dongboot 团队能独立用 CLI 跑 4 种 Profile
- [ ] 端到端一次通过率 > 80%
- [ ] 平均一次完整 Pipeline 耗时 < 8h（new-feature）
- [ ] Bug/缺陷 < 5 个 P1

### P1 关键风险
- 编码锚点约束太强 → 通过 adapter 配置可调
- Stage Runner 性能 → 用并发 + 缓存

---

## 三、Phase 2: 记忆（M3-M4）

> **核心：让 SDLC 系统"读过"项目、记住经验、越用越好用**

### M3：3 层 KB + sdlc init

#### Week 9-10: 扫描器
- 项目扫描器（基础扫描、技术栈、组件、规范反推）
- 文件指纹 + 增量检测
- 模板机制（团队模板、公司模板）
- 写入位置：`doc/kb/`

#### Week 11-12: KB 写入 API
- KB 类（KnowledgeBase）：read/write/diff
- 11 个 KB 文件的 schema 与生成器
- 人工确认机制（conventions.md 需用户确认）
- CLAUDE.md / AGENTS.md 自动同步

### M4：进化机制 + 上下文更新

#### Week 13: 进化引擎
- 模式提取（从代码相似度 → patterns.md）
- 反模式检测（从 lint/CR/test → antipatterns.md）
- ADR 自动入库（从 s-design stage）
- runbook 自动入库（从 s-deploy / s-mon / hotfix）

#### Week 14: 上下文更新钩子
- post-stage hooks（每个 stage 完成后必触发）
- 元数据更新（meta.json kb_updates 字段）
- 审计（audit.log 新增 kb_updated 事件）
- Subagent 自适应（注入 KB context）

#### Week 15-16: Subagent 自适应 + 长期 KB
- ~/.sdlc/kb/global/ 跨项目库
- ~/.sdlc/kb/team/ 团队库
- 越用越准（learned_preferences + known_mistakes）
- 季度 KB health check

### P2 验收标准
- [ ] 1 个新项目 `sdlc init` 5min 内生成完整 doc/kb/
- [ ] Pipeline 完成后 KB 自动更新（components/patterns/antipatterns）
- [ ] Subagent 注入 KB context，CR 一次通过率 > 85%
- [ ] 反模式库覆盖团队 90% 已知反模式
- [ ] 模式复用率 > 50%（同类型需求）

### P2 关键风险
- KB 漂移（KB 与代码脱节）→ 周一 reconcile + CI 检查
- 写入 KB 性能 → 异步 + diff-only
- Subagent context 过长 → 智能摘要 + 相关性排序

---

## 四、Phase 3: 扩展（M5-M6）

### M5：5 个主流 adapter

#### Week 17-18: spring-boot / python-flask / node-express
- spring-boot adapter：与 dongboot 共享 dong 系列组件（可选）
- python-flask adapter：DongDAL 替换为 SQLAlchemy、DongThread 替换为 ThreadPoolExecutor
- node-express adapter：ts/js 全套、npm test

#### Week 19-20: frontend-react / go-gin
- frontend-react：jest + cypress、component test
- go-gin：go test、go vet

### M6：Profile 完善 + Skill 完善

#### Week 21: 6 个新 Profile
- migration：双写/灰度/回滚演练
- performance：profiling + benchmark
- security：SAST + DAST + 渗透
- docs-only：只跑 docs-update
- test-only：只跑 unit-test
- review-only：只跑 cr

#### Week 22: 5 个新 Profile
- deploy-only：只跑 deploy
- monitor-only：只跑 monitor-setup
- greenfield：完整全流程（10 stage）
- poc：极简（3 stage）
- compliance：含法律审核 Gate

#### Week 23-24: Skill 完善
- MultiSkillCoordination 规则全 adapter 适配
- 安全 Skill 集成（SAST/DAST）
- 数据迁移 Skill 集成（Flyway/Liquibase）
- 性能 Skill 集成（profiling）

### P3 验收标准
- [ ] 5 个团队（每个 1 个 adapter）能独立用
- [ ] 10 个 Profile 全覆盖
- [ ] Pipeline 复用率 > 70%（同类型需求）
- [ ] 平均端到端一次通过率 > 85%

### P3 关键风险
- adapter 间代码重复 → 抽取公共库
- Profile 难理解 → 文档 + 视频教程

---

## 五、Phase 4: 完善（M7-M8）

### M7：全 adapter + 全 Profile

#### Week 25-26: 8 个新 adapter
- python-django / python-fastapi
- node-nest / frontend-vue
- go-kratos
- mobile-android / mobile-ios / mobile-flutter
- infra-terraform / infra-helm
- data-spark
- library-publish
- no-tech

#### Week 27-28: 4 个新 Profile + 治理
- security：SAST/DAST
- compliance：含法律 Gate
- performance：profiling
- 治理：审计上链、合规报告、ROI 度量

### M8：企业级 + 商业化

#### Week 29: 治理
- 审计上链（hash chain）
- 合规报告自动出
- ROI 度量（节省时间 / 减少缺陷 / 加速发布）
- 权限分级（PM/TL/SRE/QA/Security）

#### Week 30-31: 商业化
- 打包为可独立产品（独立 CLI + SaaS 平台）
- 文档站 + 视频教程
- 模板市场（用户分享 Profile / Adapter / Stage）
- 5 个外部团队 PoC

#### Week 32: 总结 + 持续
- 收集全部反馈
- 写 v3.0 规划
- 引入更多 LLM（GPT-4 / Claude / Gemini 混合）
- 引入 A2A（Agent-to-Agent）协议

### P4 验收标准
- [ ] 18 adapter 全覆盖、14 Profile 全覆盖
- [ ] 至少 10 个团队 / 公司能用
- [ ] 工具产出可商业化（独立产品 / SaaS）
- [ ] 总 ROI 可量化

### P4 关键风险
- Adapter 维护成本 → 用 adapter 市场 + 模板化
- 商业化合规 → 法务介入

---

## 六、团队规模建议

| 阶段 | 团队规模 | 角色 |
|------|----------|------|
| P1 | 1-3 人（小团队试点） | 1 主程 + 1 领域专家 + 1 PM |
| P2 | 3-5 人（KB/记忆） | + KB 维护 + Subagent 调优 |
| P3 | 5-10 人（多团队扩展） | + 多 adapter 维护 + Skill 维护 |
| P4 | 10-20 人（企业级） | + 安全 + 治理 + 产品 + 商业化 |

---

## 七、关键里程碑

```
M2 末: MVP 完成
       ↓
       灰度 1 团队（dongboot）
       ↓
M4 末: 记忆层完成（KB + init + 进化）
       ↓
       1 团队能 init + KB 自动更新
       ↓
M6 末: 5 adapter + 10 Profile
       ↓
       灰度 5 团队
       ↓
M8 末: 18 adapter + 14 Profile
       ↓
       推广全公司 / 商业化
```

---

## 八、关键资源与依赖

### 8.1 工具
- LLM: Claude Opus（架构/CR）/ Sonnet（编码/测试）/ Haiku（轻量）
- 主控: opencode（首选）/ claude code（备选）
- MCP: dongboot_analyzer / dongboothotserver / recommend_dongboot_version / internal-rpctimeout
- Skills: 已列出 11 个核心 Skill

### 8.2 数据
- Stage 库（YAML）
- Adapter 库（YAML）
- Profile 库（YAML）
- Subagent 池（YAML + Prompt 模板）
- 历史 Pipeline 数据（用于优化）
- KB 数据（项目内 doc/kb/ + 全局 ~/.sdlc/kb/）

### 8.3 文档
- 15 份文档（已完成 v1.0 + v2.0 + v2.1）
- 用户指南 + 视频教程
- 最佳实践库
- KB 模板（团队 / 公司）

---

## 九、度量指标（KPI）

### 9.1 效率
- 端到端一次通过率
- 平均单 stage 耗时
- 平均端到端总耗时
- LLM 成本 / 需求
- Pipeline 复用率
- **KB init 耗时**
- **KB 更新频率（每周更新文件数）**

### 9.2 质量
- P0/P1 缺陷数
- Code Review 通过率
- 测试覆盖率
- 部署成功率
- 线上事故数
- **反模式发现 → 入库时间**
- **模式复用率**

### 9.3 业务
- 需求吞吐量（个 / 周）
- 上线周期（天）
- 团队满意度
- ROI（节省工时 / 投入）
- **新成员 onboarding 速度**（基于 KB）

### 9.4 治理
- 审计完整性（hash chain 验证）
- 合规覆盖率
- 权限合规率
- Adapter 一致性
- **KB 完整度**（每月打分）
- **KB 新鲜度**（30 天内更新比例）

---

## 十、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| LLM API 不稳定 | 高 | 高 | 多模型 fallback、缓存、重试 |
| 编码锚点约束太严 | 中 | 中 | 可配置、按 adapter 调 |
| adapter 维护成本 | 中 | 中 | 模板化、用户共建 |
| Profile 难理解 | 中 | 低 | 视频教程 + 案例库 |
| 安全合规 | 低 | 高 | 法务介入、审计上链 |
| 团队抵触 | 中 | 中 | 灰度推广 + 培训 |
| **KB 漂移** | **中** | **高** | **周一 reconcile + CI 检查 + KB health check** |
| **KB 写入性能** | **中** | **中** | **异步 + diff-only + 缓存** |
| **Subagent context 过长** | **中** | **中** | **智能摘要 + 相关性排序 + 分段注入** |

---

## 十一、版本

- v2.0 (2026-06-05): 6 个月 3 阶段路线图
- v2.1 (2026-06-05): 8 个月 4 阶段（含 P2 记忆层）
