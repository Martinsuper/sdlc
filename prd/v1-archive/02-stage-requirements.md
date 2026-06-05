# 02 - Stage 1 需求拆解

## 一、目标

将输入的 PRD（产品需求文档）拆解为**可被工程师直接评审 + 可被 AI 直接消费**的结构化产物。

## 二、输入

| 类型 | 来源 | 必填 |
|---|---|---|
| PRD 主文档 | 产品/业务方 | 是 |
| 用户故事背景 | PRD 内嵌 | 是 |
| 数据字典（如有） | 数据团队 | 否 |
| 关联系统清单 | 架构师 | 否 |
| 历史变更记录 | 上线记录 | 否 |

**前置约束**：
- PRD 必须包含明确业务目标（否则**降级为 D 类错误**，升级人工）
- 关键名词在 PRD 中有定义
- 验收标准至少有 1 条可量化指标

## 三、Subagent 调度

### 3.1 派发命令

```
task(
  subagent_type: "general",
  description: "需求拆解",
  prompt: "[requirements-analyst prompt，见 10-subagent-spec.md §2]"
)
```

### 3.2 输入参数（JSON Schema）

```json
{
  "prd_path": "string, required, PRD 文件绝对路径",
  "feature_id": "string, required, 业务唯一标识",
  "context_hints": {
    "related_systems": ["string, 系统名"],
    "tech_stack": ["string, e.g. internal-rpc/MySQL/JIMDB"],
    "business_domain": "string, 业务域"
  }
}
```

## 四、产物模板

输出文件：`prd/{feature_id}/01-requirements.md`

```markdown
# 需求拆解：{feature_id} - {feature_name}

> 源 PRD：{prd_path}  
> 拆解时间：{timestamp}  
> 拆解 Subagent：requirements-analyst v1.0

## 1. 业务目标
{2-3 句话描述业务要解决的核心问题}

## 2. 用户故事
| 编号 | 角色 | 动作 | 价值 |
|---|---|---|---|
| US-001 | 买家 | 在结算页使用优惠券 | 降低实付 |
| US-002 | 运营 | 创建优惠券活动 | 引流拉新 |
| ... | ... | ... | ... |

## 3. 功能清单
### 3.1 主流程
- F-001 优惠券发放
- F-002 优惠券核销
- F-003 优惠券退款回滚

### 3.2 异常流程
- E-001 优惠券已过期
- E-002 优惠券已被使用
- E-003 优惠券不满足使用门槛

## 4. 验收标准（Given-When-Then）
| 编号 | Given | When | Then |
|---|---|---|---|
| AC-001 | 用户有可用优惠券 | 提交订单 | 优先使用面额最大且未过期的券 |
| AC-002 | 用户无可用优惠券 | 提交订单 | 跳过核销逻辑，不报错 |
| ... | ... | ... | ... |

## 5. 边界与异常
- **数据边界**：单用户最多持有 X 张券、单订单最多使用 Y 张
- **时间边界**：活动开始/结束时间、券有效期
- **性能边界**：QPS ≥ X，P99 ≤ Yms
- **资金边界**：涉及资金流时必须明确对账方式

## 6. 影响面分析
| 影响系统 | 影响类型 | 影响范围 | 风险等级 |
|---|---|---|---|
| 订单系统 | 数据写入 | 新增 coupon_used 字段 | 中 |
| 库存系统 | 无 | - | - |
| 财务系统 | 退款流程 | 增加回滚逻辑 | 高 |

## 7. 非功能需求
- 安全：XSS 防御、限流
- 可用性：99.99%
- 可观测：关键指标埋点

## 8. 开放问题（须 Gate 1 解决）
- [ ] Q1：券是否可叠加？
- [ ] Q2：过期提醒是实时还是定时扫描？
- [ ] Q3：与现有会员等级券是否冲突？

## 9. PRD 引用映射
| PRD 段落 | 对应需求 |
|---|---|
| §3.1 业务背景 | §1 业务目标 |
| §4.2 核心流程 | §2 US-001/002 |
| ... | ... |
```

## 五、Subagent 内部工作流

```
1. Read PRD 主文档
2. Extract 业务目标（§1）
3. Generate 用户故事（§2）
   - 主动识别角色（从 PRD 文本中提取）
   - 按"动作-价值"模板生成
4. Derive 功能清单（§3）
   - 主流程：核心场景
   - 异常流程：失败/边界场景
5. Compose 验收标准（§4）
   - 每个功能至少 1 条 G/W/T
   - 必须可量化
6. Analyze 影响面（§6）
   - 基于已有系统清单（context_hints.related_systems）
   - 风险等级：低/中/高
7. Surface 开放问题（§8）
   - PRD 未明确说明的，列出来供 Gate 1 决策
8. Map PRD 引用（§9）
   - 每个产物章节对应 PRD 段落
   - 用于审计追溯
```

## 六、Gate 1 评审规范

详见 [09-human-gates.md §1](./09-human-gates.md)。

**核心检查项**：
1. 业务目标是否准确反映 PRD 意图
2. 用户故事是否完整（角色无遗漏）
3. 异常流程是否覆盖（至少 5 条）
4. 验收标准是否可量化（每条都有 Then）
5. 开放问题是否被识别（≥ 0 条）

**驳回典型场景**：
- PRD 描述不清导致 Subagent 猜测 → 标记 D 类错误，回退
- 用户故事遗漏关键角色 → 回退
- 验收标准含"正常""正确"等模糊词 → 回退

## 七、与现有 Skill 的协同

| 场景 | 调用的 Skill |
|---|---|
| PRD 在 internal-docs | `internal-docs-reader` |
| 需对比历史需求 | `find-skills`（找历史档案） |
| 需求涉及数据查询 | `db-query` |

## 八、异常处理

| 异常 | 检测方式 | 处理 |
|---|---|---|
| PRD 文件不存在 | 读文件 404 | D 类，升级 |
| PRD 长度 < 200 字 | 字数统计 | 标记"PRD 过简" + 升级 |
| PRD 含敏感信息 | 关键词扫描（身份证/手机号） | 脱敏后输入 Subagent |
| Subagent 输出超时 | 超时 10 分钟 | 重试 1 次，仍失败则 D 类 |

## 九、产出物归档

- 位置：`prd/{feature_id}/01-requirements.md`
- 同时归档 `prd/{feature_id}/meta.json`：
  ```json
  {
    "feature_id": "...",
    "stage": 1,
    "subagent": "requirements-analyst",
    "duration_sec": 600,
    "input_hash": "sha256:...",
    "output_hash": "sha256:...",
    "gate1_status": "pending|approved|rejected",
    "gate1_reviewer": "...",
    "gate1_timestamp": "..."
  }
  ```
