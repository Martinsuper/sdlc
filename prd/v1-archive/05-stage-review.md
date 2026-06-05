# 05 - Stage 4 代码评审

## 一、目标

通过**独立的 Reviewer-only Subagent** 对 Stage 3 生成的代码进行**只读**评审，输出结构化评审报告。  
**关键约束**：Reviewer Subagent 没有任何修改权限，避免自我合理化。

## 二、输入

| 类型 | 来源 | 必填 |
|---|---|---|
| Git diff（vs base） | Stage 3 commit | 是 |
| `02-design/` 全套 | Stage 2 | 是 |
| `01-requirements.md` | Stage 1 | 是 |
| 团队规范 | `~/.claude/rules/coding-style.md` | 是 |
| 历史 CR 评论 | 仓库 `.github/` 或 Code Review 平台 | 否 |

## 三、Subagent 调度

### 3.1 派发命令

```
task(
  subagent_type: "general",
  description: "代码评审",
  prompt: "[reviewer prompt，见 10-subagent-spec.md §5]"
)
```

### 3.2 工具权限（硬约束）

| 工具 | 权限 |
|---|---|
| read / glob / grep | ✅ |
| write | ❌ **禁止** |
| edit | ❌ **禁止** |
| bash | ⚠️ 仅 `git diff`、`git log`、`find`、`ls` |
| MCP | ❌ |

**违规检测**：在 Subagent 上下文层禁用 edit/write 工具；通过 `task` prompt 显式声明"你只能阅读，禁止修改"。

## 四、评审维度

| 维度 | 权重 | 关注点 |
|---|---|---|
| **功能正确性** | 30% | 业务逻辑是否实现需求 |
| **设计一致性** | 20% | 是否符合 Stage 2 设计 |
| **代码规范** | 10% | 命名、注释、风格 |
| **安全性** | 15% | 注入、越权、敏感信息 |
| **性能** | 10% | N+1、大循环、慢 SQL |
| **可维护性** | 10% | 复杂度、重复、命名 |
| **测试覆盖** | 5% | 单测是否覆盖关键路径 |

## 五、严重度分级

| 级别 | 含义 | 是否阻塞合并 | 触发人工 Gate 3 |
|---|---|---|---|
| **P0-Blocker** | 安全漏洞、数据丢失风险、阻塞性问题 | ✅ | ✅ |
| **P1-Critical** | 性能严重退化、关键功能缺失 | ✅ | ✅ |
| **P2-Major** | 设计偏差、覆盖明显不足、潜在 bug | ⚠️ 累计 3+ 阻塞 | ❌ |
| **P3-Minor** | 规范、命名、注释、轻微风格 | ❌ | ❌ |
| **P4-Suggestion** | 改进建议 | ❌ | ❌ |

**Gate 3 触发条件**：
- 存在 ≥ 1 个 P0
- 存在 ≥ 1 个 P1
- 存在 ≥ 3 个 P2

否则 Stage 4 自动通过，进入 Stage 5。

## 六、产物模板

输出文件：`prd/{feature_id}/04-review.md`

```markdown
# 代码评审报告：{feature_id} - {feature_name}

> 评审时间：{timestamp}  
> 评审对象：commit {hash}  
> 评审人：reviewer Subagent v1.0  
> 结论：✅ 通过 / ⚠️ 需修改 / ❌ 驳回

## 1. 总结
- 总变更：N 个文件，M 行新增
- 问题数：P0: x, P1: y, P2: z, P3: a, P4: b
- 评审耗时：N 秒
- 是否触发 Gate 3：是/否

## 2. 详细问题

### [P1] CR-001: N+1 查询风险
- **位置**：`CouponServiceImpl.java:42`
- **描述**：循环中调用 `couponDao.findById()`，单次请求可能触发 100+ SQL
- **建议**：
  ```java
  // 改为批量查询
  List<Coupon> coupons = couponDao.findByIds(ids);
  ```
- **影响**：性能下降 10x+
- **关联需求**：US-001

### [P2] CR-002: 异常处理不完整
- ...

### [P3] CR-003: 命名建议
- ...

## 3. 设计一致性检查
| ADR | 是否实现 | 备注 |
|---|---|---|
| ADR-001 券码生成 | ✅ | - |
| ADR-002 库存扣减 | ⚠️ | 未使用 DongLock |
| ADR-003 超时与重试 | ✅ | - |

## 4. 规范符合度
- Checkstyle：✅ 通过
- PMD：⚠️ 2 个警告
- 单测覆盖：65%（骨架）

## 5. 测试覆盖分析
| 路径 | 是否覆盖 | 备注 |
|---|---|---|
| 正常路径 | ✅ | 骨架已生成 |
| 异常：券不存在 | ✅ | TODO |
| 异常：已使用 | ✅ | TODO |
| 异常：已过期 | ❌ | 缺失 |
| 边界：金额为 0 | ❌ | 缺失 |

## 6. 安全检查
- [x] SQL 注入：使用 DongDAL 预编译
- [x] XSS：输入已转义
- [x] 越权：用户 ID 校验通过 token
- [x] 敏感字段：日志已脱敏

## 7. 性能评估
- [x] 无 N+1
- [ ] 存在循环 SQL（见 CR-001）
- [x] 缓存使用合理

## 8. 是否需 Gate 3
是 / 否

理由：...

## 9. 建议的修复顺序
1. CR-001 (P1) - 必须修复
2. CR-002 (P2) - 建议修复
3. CR-003 (P3) - 可选
```

## 七、Subagent 内部工作流

```
1. Read 02-design/ + 01-requirements.md（建立"应该是什么样"的认知）
2. git diff base..HEAD（建立"实际是什么样"的认知）
3. Read 团队规范
4. 静态分析（自己跑 checkstyle/pmd）
5. Diff 识别（哪些文件变了）
6. 逐文件评审（按 7 大维度）
7. 关联检查（设计 vs 实现）
8. 安全检查（专项）
9. 性能检查（专项）
10. 测试覆盖检查
11. 严重度分级
12. Gate 3 决策（基于规则）
13. Output 04-review.md
```

## 八、Gate 3 评审规范

详见 [09-human-gates.md §3](./09-human-gates.md)。

**核心检查项**：
1. P0/P1 修复方案是否合理
2. P2 数量是否可接受
3. 设计一致性偏差是否需要回到 Stage 2
4. 性能/安全 P1 是否有完整缓解

**驳回典型场景**：
- P1 修复需改架构 → 回退 Stage 2
- 修复引入新问题 → 重新 Stage 3
- 多个 P0 → 升级到 TL 处理

## 九、修复循环

Gate 3 驳回后的循环：

```
Stage 4 (CR 失败)
    ↓
回到 Stage 3
    ↓
重新跑 Stage 4
    ↓
再次 Gate 3
    ↓
最多 3 轮；超过则升级到 D 类（人工编码）
```

## 十、产出物归档

更新 `meta.json`：

```json
{
  "stage": 4,
  "subagent": "reviewer",
  "p0_count": 0,
  "p1_count": 1,
  "p2_count": 2,
  "p3_count": 5,
  "p4_count": 3,
  "gate3_triggered": true,
  "gate3_result": "approved_with_p1_fix",
  "review_duration_sec": 180
}
```
