# 06 - Stage 5 测试

## 一、目标

通过**单元测试 + R2 录制回放 + 自动回归**三层保障，将代码质量从"能跑"提升到"健壮"。  
本阶段不要求 100% 覆盖率，但**关键路径必须覆盖**。

## 二、输入

| 类型 | 来源 | 必填 |
|---|---|---|
| Stage 3 业务代码 | Git | 是 |
| Stage 3 单测骨架 | Git | 是 |
| `02-design/` | Stage 2 | 是 |
| `01-requirements.md` | Stage 1 | 是 |
| R2 录制数据 | 生产/预发 | 否（首条业务线时为必填） |
| 团队覆盖标准 | 规范 | 是（默认核心 80%/边缘 60%） |

## 三、子流水线

```
Stage 5 拆分 3 个子任务（部分并行）：

  ┌─→ 单元测试增强  ──┐
  │                    ├─→ 测试报告 → 自动 Gate
  ├─→ 集成测试（R2） ──┤
  │                    │
  └─→ 回归用例选择 ───┘
```

### 3.1 并行度

| 子任务 | 依赖 | 派发时机 |
|---|---|---|
| 单元测试增强 | 单测骨架 | Stage 4 通过后立即 |
| 集成测试 R2 | 业务代码 | Stage 4 通过后立即 |
| 回归用例选择 | 接口清单 | Stage 4 通过后立即 |

## 四、子任务 1：单元测试增强

### 4.1 Subagent

`tester-unit`（详见 10-subagent-spec.md §6.1）

### 4.2 工具权限

| 工具 | 权限 |
|---|---|
| read/write/edit | ✅ 仅限 `src/test/` |
| bash | ✅ `mvn test` |
| MCP（DongMock） | ✅ |

### 4.3 必须调用的 Skill

| 场景 | Skill |
|---|---|
| DongBoot 工程单测 | `UnitTest` |
| R2 录制单测 | `R2UnitTest` / `R2UnitTestV2` / `R2ReplayUnitTest` |
| 多 skill 协同 | `MultiSkillCoordination` |

### 4.4 产物

```
src/test/java/.../CouponServiceImplTest.java   # 增强后的单测
target/surefire-reports/                        # 测试报告
```

### 4.5 增强规则

针对 Stage 3 留下的 TODO 标记，按以下顺序补全：

| 优先级 | 场景 | 实现方式 |
|---|---|---|
| P0 | 正常路径 | 真实业务断言 |
| P0 | 异常路径 | exception assertion |
| P1 | 边界值 | 0/null/最大值/最小值 |
| P1 | 并发场景 | 多线程测试 |
| P2 | 性能 | `@Timeout` + benchmark |

### 4.6 Mock 策略

**强制使用 DongMock**（详见 `UnitTest` Skill 中的 `dongmock-integration.md`）：

```java
@ExtendWith(DongMockExtension.class)
public class CouponServiceImplTest {
    @MockMethod(target = CouponDao.class)
    private CouponDao couponDao;
    
    @Test
    public void testUseCoupon_Success() {
        // DongMock DSL
        couponDao.mock("findById").when(1L).thenReturn(buildCoupon());
        
        Result<CouponDTO> result = couponService.useCoupon(buildRequest());
        
        assertThat(result.isSuccess()).isTrue();
    }
}
```

**禁止**：
- 全部用纯 Mockito（丢失 DongBoot 上下文）
- 跳过 Mock 直接打真实 DB

## 五、子任务 2：集成测试（R2 录制回放）

### 5.1 Subagent

`tester-integration`（详见 10-subagent-spec.md §6.2）

### 5.2 流程

```
1. 选择 R2 录制数据（生产/预发真实流量）
2. 调用 R2UnitTest 跑回放
3. 对比录制与回放结果
4. 标记差异
5. 输出报告
```

### 5.3 必调用 Skill

- `R2UnitTestV2`（三阶段精准生成，默认入口）
- `R2UnitTest`（V1 兜底）
- `R2ReplayUnitTest`（专项）

### 5.4 通过条件

- R2 回放成功率 ≥ 95%
- 关键差异已标注原因（业务变更/环境差异）
- 0 个未解释差异

## 六、子任务 3：回归用例选择

### 6.1 Subagent

`tester-regression`（详见 10-subagent-spec.md §6.3）

### 6.2 流程

```
1. Scan 本次变更涉及的接口
2. 调用 AutoRegression MCP
3. 选择关联的回归场景
4. 输出回归计划
```

### 6.3 必调用 Skill

`AutoRegression`

### 6.4 产物

`prd/{feature_id}/05-regression-plan.md`

```markdown
# 回归计划

## 接口影响
| 接口 | 涉及回归场景 | 选择状态 |
|---|---|---|
| CouponQueryService.queryAvailableCoupons | 23 | 选中 5 |
| OrderService.submit | 47 | 选中 3 |

## 用例列表
- REGR-001: 订单提交-正常
- REGR-002: 订单提交-库存不足
- ...

## 执行结果
（执行后填充）
```

## 七、合并与决策

主对话收集 3 个子任务结果后：

```python
def decide_gate():
    unit = unit_test_result
    integration = r2_result
    regression = regression_result
    
    if unit.coverage < 0.8 and unit.critical_paths_covered:
        return "warn:low_coverage"  # 警告但不阻塞
    if unit.failed > 0:
        return "fail:unit_failed"
    if integration.diff_rate > 0.05:
        return "fail:integration_diff"
    if regression.failed > 0:
        return "fail:regression_failed"
    return "pass"
```

## 八、Gate 决策

**Stage 5 默认自动通过**，仅在以下情况触发人工介入：

- 单测覆盖率 < 60%
- 关键 P0 路径未覆盖
- R2 回放失败率 > 5%
- 回归用例失败

否则进入 Stage 6。

## 九、产出物

`prd/{feature_id}/05-test-report.md`

```markdown
# 测试报告

## 单测
- 类数：12
- 方法数：48
- 覆盖率：行 78% / 分支 65%
- 失败：0
- 跳过：2（性能测试，仅预发跑）

## 集成（R2）
- 用例数：10
- 成功：9
- 失败：1（已知差异：环境相关，已标注）

## 回归
- 计划：8 个用例
- 执行：8
- 通过：8

## 结论
✅ 通过，可进入 Stage 6
```

## 十、产出物归档

更新 `meta.json`：

```json
{
  "stage": 5,
  "subagent": "tester",
  "subagents_count": 3,
  "unit_coverage_line": 0.78,
  "unit_coverage_branch": 0.65,
  "r2_total": 10,
  "r2_passed": 9,
  "r2_failed": 1,
  "regression_total": 8,
  "regression_passed": 8,
  "gate_decision": "pass"
}
```
