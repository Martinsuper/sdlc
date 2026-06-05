# 11. Subagent 与 Skill 机制 (v2.0)

> **Subagent = 隔离的 LLM 工作单元**  
> **Skill = 可复用的领域知识包**  
> v2.0 解除 v1.0 的 DongBoot 硬绑定，Subagent 通用化设计

---

## 一、Subagent 总体设计

### 1.1 设计目标

| 维度 | 目标 |
|------|------|
| 隔离 | 任务间互不影响（独立 context、独立工具权限） |
| 可复用 | 同一 Subagent 可被多 Stage 调用 |
| 可替换 | 通过 prompt 模板 + adapter override 切换实现 |
| 可观测 | token/耗时/工具调用全埋点 |
| 可调优 | 模型选择、温度、并发数可配 |

### 1.2 Subagent 注册表

```yaml
# ~/.claude/agents/agents.yaml
agents:
  # ============ 通用角色（v1.0 沿用，去 DongBoot 绑定）============
  requirements-analyst:
    name: 需求分析师
    model: sonnet
    temperature: 0.3
    tools: [Read, Write, Grep, Glob, Bash(ls/cat), TodoWrite, Skill, MCP(repo_context)]
    skills: [DongLog, MultiSkillCoordination, FindSkills]
    default_stage: clarify
    max_concurrent: 3

  architect:
    name: 架构师
    model: opus
    temperature: 0.4
    tools: [Read, Write, Grep, Glob, Bash(ls), TodoWrite, Skill, MCP(repo_context)]
    skills: [DongLog, MultiSkillCoordination, FindSkills, McpBuilder]
    default_stage: design
    max_concurrent: 2

  reviewer:
    name: 评审员
    model: opus
    temperature: 0.2
    tools: [Read, Grep, Glob, Bash(ls), Skill]   # 只读，无 Write
    skills: [DongLog, MultiSkillCoordination, FindSkills]
    default_stage: cr
    max_concurrent: 3
    read_only: true

  tester-unit:
    name: 单元测试
    model: sonnet
    temperature: 0.3
    tools: [Read, Write, Bash(mvn test), Bash(gradle test), Skill, MCP(repo_context)]
    skills: [UnitTest, DongLog, DongMock]
    default_stage: unit-test
    max_concurrent: 3

  tester-integration:
    name: 集成测试
    model: sonnet
    temperature: 0.3
    tools: [Read, Write, Bash(docker compose), Skill, MCP(repo_context)]
    skills: [UnitTest, DongLog, MultiSkillCoordination]
    default_stage: integration-test
    max_concurrent: 2

  tester-regression:
    name: 回归测试
    model: sonnet
    temperature: 0.2
    tools: [Read, Write, Bash(mvn test), Skill, MCP(repo_context, dongboothotserver)]
    skills: [AutoRegression, R2UnitTestV2, R2UnitTest, R2ReplayUnitTest, DongLog]
    default_stage: regression
    max_concurrent: 2

  deployer:
    name: 部署
    model: sonnet
    temperature: 0.1
    tools: [Read, Bash(docker/kubectl), Skill, MCP(deploy)]
    skills: [DongBootHotswapTroubleshoot, DeployBizLogTroubleshoot, MultiSkillCoordination]
    default_stage: deploy
    max_concurrent: 1

  sre-writer:
    name: SRE 文档
    model: sonnet
    temperature: 0.4
    tools: [Read, Write, Grep, Skill, MCP(monitor)]
    skills: [DongMonitorDashboard, MultiSkillCoordination, FindSkills]
    default_stage: monitor-setup
    max_concurrent: 2

  # ============ 编码类（多 Adapter 实现）============
  coder-backend:
    name: 后端编码（通用）
    model: sonnet
    temperature: 0.2
    tools: [Read, Write, Edit, Grep, Glob, Bash(mvn/gradle/go test/npm), Skill, MCP]
    skills: [DongLog, MultiSkillCoordination, FindSkills]
    default_stage: implement-backend
    max_concurrent: 2
    adapter_overrides:
      dongboot: coder-jvm-dongboot
      spring-boot: coder-jvm-spring
      python-flask: coder-python-flask
      python-fastapi: coder-python-fastapi
      python-django: coder-python-django
      go-gin: coder-go-gin
      go-kratos: coder-go-kratos
      node-express: coder-nodejs-express
      node-nest: coder-nodejs-nest

  coder-frontend:
    name: 前端编码
    model: sonnet
    temperature: 0.2
    tools: [Read, Write, Edit, Bash(npm/yarn test), Skill, MCP]
    skills: [DongLog, MultiSkillCoordination]
    default_stage: implement-frontend
    max_concurrent: 2
    adapter_overrides:
      frontend-react: coder-frontend-react
      frontend-vue: coder-frontend-vue

  coder-mobile:
    name: 移动端编码
    model: sonnet
    temperature: 0.2
    tools: [Read, Write, Edit, Skill]
    skills: [DongLog, MultiSkillCoordination]
    default_stage: implement-mobile
    max_concurrent: 1
    adapter_overrides:
      mobile-android: coder-mobile-android
      mobile-ios: coder-mobile-ios
      mobile-flutter: coder-mobile-flutter

  coder-infra:
    name: 基础设施编码
    model: sonnet
    temperature: 0.1
    tools: [Read, Write, Edit, Bash(terraform/kubectl), Skill, MCP]
    skills: [DongLog, MultiSkillCoordination]
    default_stage: implement-infra
    max_concurrent: 1
    adapter_overrides:
      infra-terraform: coder-terraform
      infra-helm: coder-helm

  # ============ 文档/维护类 ============
  doc-writer:
    name: 文档
    model: sonnet
    temperature: 0.5
    tools: [Read, Write, Grep, Skill]
    skills: [DongLog, MultiSkillCoordination]
    default_stage: docs-update
    max_concurrent: 3

  refactorer:
    name: 重构
    model: sonnet
    temperature: 0.2
    tools: [Read, Write, Edit, Grep, Glob, Bash(test), Skill]
    skills: [DongLog, MultiSkillCoordination, FindSkills]
    default_stage: refactor
    max_concurrent: 1
    adapter_overrides:
      dongboot: refactorer-jvm-dongboot
      spring-boot: refactorer-jvm-spring
      python-flask: refactorer-python

  migrationer:
    name: 数据迁移
    model: sonnet
    temperature: 0.1
    tools: [Read, Write, Edit, Bash(docker/mvn), Skill, MCP]
    skills: [DongDAL, DongSequence, MultiSkillCoordination]
    default_stage: migration
    max_concurrent: 1
    adapter_overrides:
      dongboot: migrationer-jvm-dongboot
      spring-boot: migrationer-jvm-spring

  # ============ 特殊：dba-agent 仅 dongboot 场景使用 ============
  dba-agent:
    name: DBA（JDG 场景）
    model: sonnet
    temperature: 0.1
    tools: [Read, Write, Bash, Skill, MCP(dongboot_analyzer, recommend_dongboot_version)]
    skills: [DongDAL, DongSequence, MultiSkillCoordination]
    default_stage: implement-backend
    max_concurrent: 1
    only_for_adapters: [dongboot]
```

---

## 二、Subagent 工具权限模型

### 2.1 权限声明

```yaml
tools:
  - Read              # 读文件
  - Write             # 写文件
  - Edit              # 改文件
  - Grep              # 搜索
  - Glob              # 文件列表
  - Bash(<pattern>)   # shell 命令（白名单 pattern）
  - Skill             # 调用 Skill
  - MCP(<server>)     # 调用 MCP 工具
```

### 2.2 权限梯度

| 权限 | 说明 | 谁可拿 |
|------|------|--------|
| 只读 | Read, Grep, Glob, Bash(ls) | reviewer |
| 编辑 | + Write, Edit, Bash(test) | coder, tester, refactorer |
| 部署 | + Bash(docker/kubectl/curl) | deployer |
| MCP 写入 | + MCP(<writable>) | dba-agent |
| Skill 调用 | 任意 | 全部 |

### 2.3 Bash 白名单

```yaml
bash_patterns:
  coder-backend: ["mvn", "gradle", "go test", "go build", "npm test", "pytest"]
  coder-frontend: ["npm", "yarn", "pnpm", "jest", "vitest"]
  deployer: ["docker", "kubectl", "helm", "aws", "az"]
  tester-unit: ["mvn test", "gradle test", "go test", "pytest", "jest"]
```

---

## 三、Subagent 生命周期

```
注册 → 加载 prompt 模板 → 分配任务 → 注入 inputs → 执行 → 收集 outputs → 释放
```

### 3.1 注册（一次）

```yaml
# ~/.claude/agents/agents.yaml 注册一次
coder-jvm-dongboot:
  inherits: coder-backend
  override:
    model: sonnet
    skills: [DongLog, DongDAL, DongCache, DongHttp, DongLock, DongThread, DongSequence, DongSchedule, internal-mq, internal-rpc, MultiSkillCoordination]
    mcp_tools: [dongboot_analyzer, dongboothotserver, recommend_dongboot_version, internal-rpctimeout]
  enabled_for_adapters: [dongboot]
  prompt_template: prompts/coder-jvm-dongboot.md
```

### 3.2 加载（每次任务启动）

1. 读取 agents.yaml
2. 加载 prompt 模板
3. 注入元数据（adapter / profile / project_id / feature_id）
4. 设置工具权限
5. 启动独立 context

### 3.3 执行

```
[Main] 调度 Subagent
   ↓
[Subagent] 接收 inputs
   ↓ 思考
[Subagent] 调 Skill / MCP / 工具
   ↓
[Subagent] 产出 outputs（写文件 + 返结构化）
   ↓
[Main] 验证 outputs（output_validation）
   ↓
[Main] 写 audit.log
```

### 3.4 释放

- context 释放（节省 token）
- 保留 metadata（audit/snapshot）
- 并发槽释放

---

## 四、Subagent 与 Adapter 的关系

### 4.1 两层映射

```
Stage (如 implement-backend)
   ↓ default_subagent
Subagent (如 coder-backend)
   ↓ adapter_overrides
Subagent 实例 (如 coder-jvm-dongboot) — 按当前 adapter 选择
```

### 4.2 优先级

1. Stage 指定 subagent → 跳过
2. Stage 指定 candidates → 用户选
3. Subagent adapter_overrides[当前 adapter] → 切换
4. 找不到 → 用 default

### 4.3 跨 adapter 行为

如果同一 Pipeline 中有多个 adapter（如 dongboot + frontend-react）：
- impl 阶段分裂为多个并行 stage
- 每个 stage 用对应 adapter 的 subagent
- unit-test 阶段分裂为多份（各 adapter 自己的 test runner）
- cr 阶段用通用 reviewer（必要时按 adapter 切）

---

## 五、Skill 机制

### 5.1 Skill 分类

| 类别 | 作用 | 示例 |
|------|------|------|
| **业务规范** | 领域最佳实践 | DongLog、BizLogger、DongCache、internal-rpc、MultiSkillCoordination |
| **测试工具** | 单测/集成/回归 | UnitTest、R2UnitTestV2、R2UnitTest、R2ReplayUnitTest、AutoRegression |
| **部署工具** | 部署/回滚 | DongBootHotswapTroubleshoot、DeployBizLogTroubleshoot |
| **运维工具** | 监控/告警 | DongMonitorDashboard |
| **辅助** | 通用增强 | FindSkills |

### 5.2 Skill 调用模型

```
Subagent 决定触发某 Skill
   ↓
读取 skill SKILL.md
   ↓
按 skill 流程执行（可能再调其它 Skill / MCP）
   ↓
返回结构化结果
```

### 5.3 Skill 协同规则

```yaml
# MultiSkillCoordination 规则
always_check:
  - DongLog         # 业务代码必带
  - internal-rpc             # RPC 调用必检
  - DongThread      # 线程池/异步必检
  - DongDAL         # DB 必检
  - DongCache       # 缓存必检
  - DongHttp        # HTTP 必检
  - DongLock        # 分布式锁必检
  - DongSequence    # 序列号必检
  - DongSchedule    # 调度必检
  - DongES          # ES 必检
  - internal-mq             # 消息必检

priority:  # 同时匹配多 skill 时
  - 安全相关（internal-rpc/MultiSkillCoordination）> 业务功能 > 优化
```

### 5.4 Skill 自动发现

通过 SKILL.md 中的 `description` 字段匹配用户输入关键词，自动列入候选。

---

## 六、Subagent 与 Skill 的协同流程

### 示例：Coder 接到 implement-backend 任务

```
1. Coder 启动，接收 inputs（设计文档/API 契约/DB schema/上下文）
2. Coder 阅读 prompt 模板
3. 模板指导：触发 MultiSkillCoordination
4. MultiSkillCoordination 扫描代码特征：
   - 出现 @internal-rpcConsumer → 触发 internal-rpc skill
   - 出现 ThreadPoolExecutor → 触发 DongThread
   - 出现 @Repository → 触发 DongDAL
   - 出现 @Cacheable → 触发 DongCache
5. Coder 顺序执行各 skill（生成代码片段）
6. Coder 写代码 + 锚点 + 单元测试骨架
7. 写 DongLog/BizLogger 埋点
8. 输出 outputs
```

### 流程图

```
┌─────────────────────────────────────────┐
│ Main: 调度 coder-backend Subagent       │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ coder-backend 启动                     │
│ - 读 prompt 模板                       │
│ - 注入 inputs                          │
│ - 设置工具权限                         │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 调用 MultiSkillCoordination skill      │
└─────────────┬───────────────────────────┘
              ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ DongDAL      │ │ DongCache    │ │ DongLog      │
│ (数据访问)   │ │ (本地缓存)   │ │ (业务日志)   │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┴────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ coder-backend 汇总 code + 锚点 + 测试骨架│
│ 写 outputs                              │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Main: 验证 output_validation           │
│ 写 audit.log                           │
│ 检查产物 hash                          │
└─────────────────────────────────────────┘
```

---

## 七、Subagent 性能调优

### 7.1 并发控制

```yaml
# ~/.claude/agents/concurrency.yaml
global_max: 8
per_agent_max:
  requirements-analyst: 3
  architect: 2
  coder-backend: 2
  tester-regression: 2
  deployer: 1
queue_strategy: fifo
timeout_minutes: 60
```

### 7.2 模型选择

按任务复杂度分：
- 高复杂（设计/架构/CR）→ Opus
- 中复杂（编码/测试）→ Sonnet
- 低复杂（CR 浅评/文档）→ Haiku

### 7.3 缓存策略

- Repo context：跨 stage 共享（1h 缓存）
- 设计文档：stage 内共享
- 同一 Subagent 同一任务：复用 context

### 7.4 失败重试

```yaml
retry:
  max_attempts: 3
  on_validation_fail: true
  on_tool_error: true
  on_rate_limit: exponential_backoff
```

---

## 八、Subagent 监控面板

```yaml
# 实时看板字段
subagent_stats:
  - agent_id
  - current_stage
  - model
  - tokens_used
  - cost_usd
  - duration_minutes
  - tool_call_count
  - skill_invocation_count
  - status
```

通过 `sdlc agent status` 查看，支持 kill/resume。

---

## 九、版本

- v2.0 (2026-06-05): 通用化 Subagent 与 Skill 设计
