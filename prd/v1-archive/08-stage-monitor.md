# 08 - Stage 7 监控与上线准备

## 一、目标

为新功能**自动生成监控大盘、告警规则、Runbook**，让 SRE 能在 5 分钟内完成上线准备。  
**本阶段末尾触发 Gate 4**。

## 二、输入

| 类型 | 来源 | 必填 |
|---|---|---|
| 业务代码 | Stage 3 | 是 |
| BizLogger 调用 | Stage 3 | 是 |
| `01-requirements.md` | Stage 1 | 是 |
| 关键路径与指标 | PM/BA | 否（可由 Subagent 推断） |
| 现有告警规则 | DUCC/监控平台 | 否 |

## 三、Subagent 调度

### 3.1 派发命令

```
task(
  subagent_type: "general",
  description: "监控与上线准备",
  prompt: "[sre-writer prompt，见 10-subagent-spec.md §8]"
)
```

### 3.2 工具权限

| 工具 | 权限 |
|---|---|
| 读 | ✅ |
| 写 | ✅ 仅 `prd/{feature_id}/07-monitor/` |
| MCP（DongMonitor） | ✅ |
| MCP（DUCC） | ⚠️ 只读 |

## 四、必调用 Skill

| Skill | 用途 |
|---|---|
| `DongMonitorDashboard` | 创建监控盘 |
| `DongLog` | 校验 BizLogger 日志格式 |
| `DongBootHotswapTroubleshoot` | 故障 Runbook 引用 |

## 五、产物清单

输出目录：`prd/{feature_id}/07-monitor/`

```
07-monitor/
├── 01-dashboard.yaml       # 监控盘配置
├── 02-alerts.yaml          # 告警规则
├── 03-runbook.md           # 故障处理手册
├── 04-metrics.md           # 关键指标说明
├── 05-slo.md               # SLO 定义
└── meta.json
```

## 六、监控盘设计

### 6.1 设计原则

- **核心指标优先**：业务核心链路 1 屏可见
- **分层监控**：业务层 → 应用层 → 资源层
- **可下钻**：每个指标都能下钻到日志

### 6.2 模板

```yaml
# 01-dashboard.yaml
dashboard:
  name: 优惠券核销-{feature_id}
  type: business
  panels:
    - title: 优惠券核销量
      query: biz-log:CouponBiz.useCoupon
      type: line
      unit: count
      
    - title: 核销成功率
      query: |
        sum(biz-log:success{CouponBiz.useCoupon}) 
        / 
        sum(biz-log:CouponBiz.useCoupon)
      type: gauge
      threshold: 0.99
      
    - title: P99 延迟
      query: p99(biz-log:duration{CouponBiz.useCoupon})
      type: line
      unit: ms
      
    - title: 异常类型分布
      query: biz-log:exception{CouponBiz.useCoupon}
      type: pie
```

调用 `DongMonitorDashboard` MCP 自动创建。

## 七、告警规则

### 7.1 三类告警

| 类型 | 触发条件 | 通知对象 | 响应 SLA |
|---|---|---|---|
| **P0-紧急** | 核心指标下跌 50%+ | oncall SRE + TL | 5 min |
| **P1-严重** | 错误率 > 1% | SRE | 15 min |
| **P2-一般** | 性能退化 | 业务 owner | 1h |

### 7.2 模板

```yaml
# 02-alerts.yaml
alerts:
  - name: 优惠券核销异常下跌
    level: P0
    condition: |
      sum(biz-log:success{CouponBiz.useCoupon}[5m])
      <
      sum(biz-log:success{CouponBiz.useCoupon}[1h]) * 0.5
    notify: oncall-sre@jd.com
    runbook: 03-runbook.md#1
    
  - name: 核销错误率高
    level: P1
    condition: |
      sum(biz-log:error{CouponBiz.useCoupon}[5m])
      /
      sum(biz-log:CouponBiz.useCoupon}[5m])
      > 0.01
    notify: sre-team@jd.com
    runbook: 03-runbook.md#2
```

## 八、Runbook 自动生成

### 8.1 内容结构

```markdown
# 故障处理手册：{feature_id} - 优惠券核销

## 0. 快速跳转
- [1. 核销量下跌](#1-核销量下跌)
- [2. 错误率高](#2-错误率高)
- [3. 延迟高](#3-延迟高)
- [4. 超发事故](#4-超发事故)

## 1. 核销量下跌
**告警**：P0 优惠券核销异常下跌
**现象**：监控盘"核销量"曲线急剧下降
**初步定位**：
1. 查看 DUCC `coupon.enabled` 是否变更
2. 查看上游订单服务是否有变更
3. 查看数据库连接池是否打满
**恢复**：
1. 如配置变更：DUCC 切回旧值
2. 如上游问题：联系上游 oncall
3. 如连接池：扩容或重启实例
**升级**：30 分钟未恢复 → TL

## 2. 错误率高
...

## 3. 延迟高
...

## 4. 超发事故
**告警**：人工巡检发现
**现象**：DBA 反馈优惠券超发
**紧急操作**：
1. 立即 DUCC 关闭 `coupon.use.enabled`
2. 调用 hot_deploy 关闭入口
3. 数据订正（详见 DBA 文档）
4. 复盘 + 改进
```

### 8.2 自动生成机制

Subagent 通过以下步骤生成：

```
1. Read 02-design/ 的风险清单
2. Read 04-review.md 的 P0/P1
3. Read 团队历史 Runbook（通过 knowledge base）
4. 对每个风险 → 1 个 Runbook 章节
5. 通过模板填充：现象/定位/恢复/升级
```

## 九、关键指标说明

```markdown
# 04-metrics.md

## 业务指标
| 指标 | 定义 | 来源 | 告警阈值 |
|---|---|---|---|
| 核销量 | useCoupon 成功次数 | biz-log:success | 下跌 50% |
| 成功率 | success / total | biz-log | < 99% |
| 平均优惠金额 | sum(faceValue) / count | biz-log | 异常上涨 30% |

## 应用指标
| 指标 | 定义 | 来源 | 告警阈值 |
|---|---|---|---|
| QPS | useCoupon 调用次数 / 秒 | 监控 | > 1000 |
| P99 延迟 | P99 of duration | 监控 | > 500ms |
| 错误率 | error / total | 监控 | > 1% |

## 资源指标
| 指标 | 来源 | 告警阈值 |
|---|---|---|
| JVM 堆使用 | JMX | > 80% |
| DB 连接池 | Druid | > 80% |
| CPU | 主机 | > 80% |
```

## 十、SLO 定义

```markdown
# 05-slo.md

## 服务等级目标
- **可用性**：99.95%（月度）
- **延迟**：P99 ≤ 500ms
- **错误率**：≤ 0.5%
- **容量**：≥ 10000 QPS

## 错误预算
- 月度错误预算：43 分钟不可用
- 消费率告警：> 50% 时 P1，> 80% 时 P0

## 度量周期
- 实时：监控盘
- 日报：自动化生成
- 周报：SRE 复盘
```

## 十一、Gate 4 评审规范

详见 [09-human-gates.md §4](./09-human-gates.md)。

**核心检查项**：
1. 监控盘是否覆盖核心业务指标
2. 告警阈值是否合理（不能太敏感/太迟钝）
3. Runbook 是否可执行（每步都有具体动作）
4. SLO 是否与 PRD 一致

**驳回典型场景**：
- 监控指标缺失 → 补指标
- 告警阈值不合理 → 调整
- Runbook 模糊 → 重写

## 十二、上线前最终清单

Gate 4 通过后，**自动产出上线 Checklist**：

```markdown
# {feature_id} 上线 Checklist

## 功能
- [x] 业务代码已合并 main
- [x] DUCC 配置已上线
- [x] DB 变更已执行

## 测试
- [x] 单测覆盖率 ≥ 80%
- [x] 集成测试通过
- [x] 回归用例通过

## 部署
- [x] develop 验证通过
- [x] staging 验证通过
- [x] pre 验证通过
- [ ] prod 灰度计划确认

## 监控
- [x] 监控盘已配置
- [x] 告警已启用
- [x] Runbook 已发布
- [x] oncall 已通知

## 业务
- [x] PM 已验收
- [x] 运营已培训
- [x] 客服 FAQ 已更新

## 上线时间窗口
- 计划：2026-06-10 02:00 - 04:00
- 批准人：TL 张三
- 应急联系：oncall SRE 李四
```

## 十三、产出物归档

更新 `meta.json`：

```json
{
  "stage": 7,
  "subagent": "sre-writer",
  "dashboard_url": "https://monitor.jd.com/d/...",
  "alerts_count": 4,
  "p0_alerts": 1,
  "runbook_sections": 4,
  "gate4_status": "approved",
  "go_live_window": "2026-06-10 02:00-04:00"
}
```
