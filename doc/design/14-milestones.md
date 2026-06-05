# 14. 里程碑 (v1.0)

> 8 个月 4 阶段 + 周级任务分解

---

## 一、整体路线

```
M1 基础设施      M2 核心功能      M3 知识与扩展     M4 完善与 GA
2 个月 (8 周)    2 个月 (8 周)    2 个月 (8 周)     2 个月 (8 周)
2026-06~07        2026-08~09        2026-10~11        2026-12~2027-01
  │                │                │                │
  v0.1.0            v0.2.0            v0.3.0            v1.0.0
  (alpha)           (beta)            (rc)              (GA)
```

**总投入**：~32 周单人开发
**关键依赖**：
- M1 → M2：脚手架跑通
- M2 → M3：5 个 stage + 5 个 subagent + 1 真实项目跑通
- M3 → M4：KB 引擎 + Adapter 框架稳定
- M4 → GA：性能 + 文档 + 社区

---

## 二、M1：基础设施 (8 周)

### 2.1 目标

- CLI 框架跑通
- 状态机/审计/配置就绪
- 1 个 Stage + 1 个 Subagent + 1 个 Adapter + 1 个 Gate 完整跑通
- dongboot 项目端到端跑通（1 个 stage）

### 2.2 任务分解

| 周 | 任务 | 产出 | 验收 |
|---|---|---|---|
| W1 | 项目初始化 | pyproject.toml + uv + ruff + mypy + pytest + pre-commit | `uv run sdlc --version` 输出 |
|   | utils 包 | pydantic / YAML / path / fs / lock / log | 测试通过 |
| W2 | cli 基础 | click 框架 + main 入口 + 19 命令 stub | `sdlc --help` 显示所有命令 |
|   | config 包 | ConfigLoader + 4 层合并 | 单测通过 |
| W3 | audit 包 | AuditLogger + JSONL + 25+ 事件 | `sdlc config show` 显示日志路径 |
|   | state 包 | StateStore + SQLite + 6 表 | `sdlc doctor` 通过 |
| W4 | llm 包（基础） | Anthropic provider + OpenAI fallback | `sdlc config test-llm` 成功 |
|   | llm cache | SQLite 缓存 + 30% 命中率 | bench 通过 |
| W5 | subagent 包（基础） | 渲染 + 循环 + tool execution | 1 个 Subagent 跑通 |
|   | prompt 渲染 | Jinja2 + 11 Subagent 配置 stub | `sdlc agent list` 显示 |
| W6 | stage 包（基础） | StageRunner + 8 步生命周期 | 1 个 stage 跑通 |
|   | gate 包（基础） | GateEngine + Decision 状态 | 1 个 gate 验证 |
| W7 | adapter 包（基础） | Adapter 协议 + Registry + Detector | dongboot 被识别 |
|   | 端到端最小路径 | 1 stage + 1 subagent + 1 adapter | dongboot 项目跑通 1 stage |
| W8 | 集成测试 | E2E 测试 + 文档骨架 + CHANGELOG | M1 demo 跑通 |

### 2.3 M1 完成标准（Definition of Done）

- ✅ 19 个 CLI 命令都有 stub 实现
- ✅ StateStore / Audit / Config / LLM Cache 可用
- ✅ dongboot 项目能跑通至少 1 个 stage（如 `s-clarify`）
- ✅ 单元测试覆盖 >= 60%
- ✅ `sdlc doctor` 通过
- ✅ README + 快速上手 文档完成
- ✅ 1 个完整 demo 录制视频

### 2.4 风险

| 风险 | 缓解 |
|---|---|
| LLM provider API 变化 | 锁版本 + 适配器模式 |
| SQLite 并发问题 | WAL 模式 + 序列化 |
| click vs typer 选错 | 调研后选 click |

---

## 三、M2：核心功能 (8 周)

### 3.1 目标

- 5 个 stage 全实现
- 5 个核心 subagent
- 完整 pipeline（含 DAG）
- Resume / Cost tracking
- 1 个真实项目端到端跑通

### 3.2 任务分解

| 周 | 任务 | 产出 | 验收 |
|---|---|---|---|
| W9 | 5 个内置 stage 完整 | clarify / design / implement / test / deploy | `sdlc stage list` 显示 |
|   | 22 stage 模板 | `sdlc/builtin/stages/*.yaml` | 单测 100% |
| W10 | pipeline builder | DAG 算法 + 拓扑排序 | `sdlc run` 自动组装 |
|   | entry detector | 12 入口识别 | 输入测试用例 |
| W11 | 5 个 subagent 完整 | analyst / architect / coder / tester / reviewer | mock LLM 跑通 |
|   | tool 完整 | 8 tool 实现 | 单测覆盖 |
| W12 | resume 实现 | 12h token + state restore | `sdlc resume <id>` 成功 |
|   | cost tracking | 实时成本 + 上限报警 | `sdlc stats` 显示 |
| W13 | 14 profile 完整 | dongboot / spring / python / ... | 自动匹配 |
|   | profile 引擎 | 加载 + 合并 + 验证 | `sdlc profile list` |
| W14 | kb scanner 完整 | 7 阶段 + 11 文件 schema | `sdlc kb scan` 显示 |
|   | kb writer 完整 | diff-only + append + async batch | 24h rollback 工作 |
| W15 | 端到端集成 | 1 真实项目（dongboot-cc）跑通全 5 stage | 完整 demo |
| W16 | 性能优化 | KB 扫描 < 1s / Stage 启动 < 100ms | bench 通过 |

### 3.3 M2 完成标准

- ✅ 5 个 stage YAML 完整可跑
- ✅ 5 个核心 subagent 完整
- ✅ dongboot-cc 项目端到端 5 stage 跑通
- ✅ Resume 12h 成功
- ✅ Cost 上限报警工作
- ✅ 14 profile 加载正确
- ✅ KB 扫描 < 1s
- ✅ 单元测试覆盖 >= 75%

### 3.4 风险

| 风险 | 缓解 |
|---|---|
| LLM 输出不稳定 | JSON schema 强约束 + 失败重试 |
| DAG 死锁 | 单测 + lint |
| 5 stage 跑太久 | 成本控制 + 并发 |

---

## 四、M3：知识与扩展 (8 周)

### 4.1 目标

- KB 引擎完整（scanner + writer + reconciler + 4 enforcer）
- Adapter 框架稳定（18+ adapter）
- Rule 引擎（547+ rules）
- Subagent 池（11+ subagents）
- Memory L2 KB 自动更新
- Init 自动化

### 4.2 任务分解

| 周 | 任务 | 产出 | 验收 |
|---|---|---|---|
| W17 | kb reconciler | 自动对账 + 7 天过期 | `sdlc kb reconcile` |
|   | exception manager | 规则例外 + 过期 | `sdlc rule exceptions` |
| W18 | rule 引擎 | 4 enforcer + 547 rules | 阻断测试 |
|   | rule 模板 | Jinja2 渲染 | 单测 |
| W19 | adapter 框架完整 | 18+ adapter 实现 | `sdlc adapter list` |
|   | dongboot adapter | 全部能力 + DongBoot 集成 | 真实 dongboot 跑 |
| W20 | subagent 池 | 11+ subagent + skill 集成 | `sdlc agent run sa-1` |
|   | skill 框架 | 9 内置 + 1 外部 | skill 调用成功 |
| W21 | memory L2 | post-stage 自动更新 KB | KB 日志可追溯 |
|   | init 自动化 | 项目扫描 → profile + adapter + rules | 30s 完成 |
| W22 | dongboot 深度集成 | DongBoot 18 adapter 全部实现 | 真实项目跑 |
|   | dongboot 迁移 | run_dongboot_migrate | `sdlc adapter dongboot migrate` |
| W23 | 端到端验证 | 2-3 真实项目（dongboot / python / nestjs） | demo 录制 |
| W24 | 性能调优 | Stage 启动 < 100ms / LLM 命中率 > 30% | bench 通过 |

### 4.3 M3 完成标准

- ✅ KB 完整引擎（scanner + writer + reconciler + enforcer）
- ✅ 18+ adapter 全部可用
- ✅ 547 rules 实现并可执行
- ✅ 11+ subagent 全部可用
- ✅ Init 30s 完成
- ✅ Memory L2 自动更新
- ✅ 2-3 真实项目 demo
- ✅ 单元测试覆盖 >= 80%

### 4.4 风险

| 风险 | 缓解 |
|---|---|
| KB 漂移 | fingerprint + diff-only |
| Adapter 兼容性 | 测试矩阵 |
| Rules 误报 | 渐进式 + 例外机制 |

---

## 五、M4：完善与 GA (8 周)

### 5.1 目标

- Gate 引擎完整（10 gate）
- 性能达标
- 完整文档
- 社区就绪
- 1.0 GA 发布

### 5.2 任务分解

| 周 | 任务 | 产出 | 验收 |
|---|---|---|---|
| W25 | gate 完整 | 10 gate 全部实现 | `sdlc gate list` |
|   | 集成到 pipeline | gate → stage 集成 | 阻断测试 |
| W26 | profile 完整 | 14 profile 全部实现 | 加载测试 |
|   | profile 自动匹配 | 输入 → profile | 准确率 100% |
| W27 | 性能优化 | 全部指标达标 | bench pass |
|   | 并发优化 | 3 stage 并发 | 跑通 |
| W28 | 文档完整 | API 文档 + 教程 + ADR | mkdocs 完整 |
|   | CHANGELOG | 完整历史 | 0.1~1.0 |
| W29 | Homebrew formula | 自动更新 | `brew install sdlc` |
|   | Docker | 多架构镜像 | `docker run sdlc/sdlc` |
| W30 | 安全审计 | bandit + pip-audit + trufflehog | 0 漏洞 |
|   | 性能测试 | locust 压测 | 100 pipeline 跑通 |
| W31 | 社区就绪 | README / CONTRIBUTING / SECURITY / CODE_OF_CONDUCT | 完整 |
|   | Issue 模板 | 3 个模板 | 可用 |
| W32 | GA 1.0 | 发布 + 公告 + 视频 | 1.0.0 on PyPI |

### 5.3 M4 完成标准

- ✅ 10 gate 全部实现
- ✅ 14 profile 全部实现
- ✅ 全部性能预算达标
- ✅ 全部文档完整
- ✅ 安全审计通过
- ✅ GA 1.0 发布

### 5.4 风险

| 风险 | 缓解 |
|---|---|
| 性能不达标 | 提前 W26 优化 |
| 文档不全 | 边写边更新 |
| 安全漏洞 | 早做审计 |

---

## 六、并行可加速项

如果想压缩到 6 个月：

| 项 | 原 | 并行后 |
|---|---|---|
| 5 stage 实现 | W9-10 | W9-10 不变 |
| 14 profile | W13-14 | W11-12 与 stage 并行 |
| kb scanner | W14 | 与 stage 并行 |
| adapter 18+ | W19-20 | W13-14 起步，并行 |
| subagent 11+ | W20 | 并行 |
| doc | W28 | 一直写 |

**关键路径**：M1 → M2 → M3 → M4 串行，**每个 M 内部可大幅并行**。

---

## 七、每日节奏

| 时段 | 内容 |
|---|---|
| 09:00-09:30 | 昨日 review + 今日计划 |
| 09:30-12:00 | 编码 |
| 12:00-13:00 | 午餐 |
| 13:00-17:00 | 编码 + 单元测试 |
| 17:00-17:30 | 提交 + PR + 写进度 |

**单日任务量**：~80-120 行代码（含测试）。

---

## 八、每周节奏

| 日 | 活动 |
|---|---|
| 周一 | 计划（10 个任务） |
| 周三 | 中期检查 |
| 周五 | 周回顾 + 录 demo |

---

## 九、关键里程碑日期

| 日期 | 里程碑 |
|---|---|
| 2026-06-05 | 启动 + 项目初始化 |
| 2026-07-31 | M1 完成（v0.1.0 alpha） |
| 2026-09-30 | M2 完成（v0.2.0 beta） |
| 2026-11-30 | M3 完成（v0.3.0 rc） |
| 2027-01-31 | M4 完成（v1.0.0 GA） |

---

## 十、度量

### 10.1 代码量

| 阶段 | 累计 LoC |
|---|---|
| M1 | ~3500 |
| M2 | ~7000 |
| M3 | ~9000 |
| M4 | ~12000 |

### 10.2 测试覆盖

| 阶段 | Unit | Integration | E2E |
|---|---|---|---|
| M1 | 60% | 10% | 5% |
| M2 | 75% | 40% | 20% |
| M3 | 80% | 70% | 50% |
| M4 | 85% | 90% | 80% |

### 10.3 性能

| 指标 | M1 | M2 | M3 | M4 |
|---|---|---|---|---|
| CLI 启动 | 1s | 500ms | 300ms | < 200ms |
| KB 扫描 100 文件 | 5s | 3s | 2s | < 1s |
| Stage 启动 | 500ms | 200ms | 150ms | < 100ms |
| LLM Cache 命中率 | 0% | 15% | 25% | 30%+ |

### 10.4 社区

| 指标 | M1 | M2 | M3 | M4 |
|---|---|---|---|---|
| GitHub Stars | 10 | 100 | 500 | 1000+ |
| PyPI 下载 | 100 | 1K | 5K | 10K+ |
| Issue 数 | < 5 | < 20 | < 50 | < 100 |
| Contributors | 1 | 1-2 | 2-3 | 3+ |

---

## 十一、退路

### 11.1 M1 失败

- 兜底：M1 只做 CLI + State + LLM（不含 subagent）
- 推迟 subagent 到 M2

### 11.2 真实项目跑不通

- 提供 mock LLM 模式（`sdlc run --mock-llm`）
- 提供 fixture 模式

### 11.3 时间延期

| 延期 | 措施 |
|---|---|
| +1 月 | 砍 P2 完善（性能、CI） |
| +2 月 | 砍 P3 知识引擎（KB Reconciler） |
| +3 月 | 砍 Adapter 数（先做 5 个） |
| +4 月+ | 砍 GA（推迟到 2027-02） |

---

## 十二、依赖

### 12.1 外部依赖

- Anthropic API
- OpenAI API
- PyPI / Homebrew
- GitHub Actions
- Docker Hub

### 12.2 内部依赖

- 完成 PRD v2.2 ✅
- 完成设计稿 15 份（W32 前）
- dongboot 18+ adapter 完整

---

## 十三、版本

- v1.0 (2026-06-05): 初版
