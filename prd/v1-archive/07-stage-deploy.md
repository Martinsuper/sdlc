# 07 - Stage 6 部署

## 一、目标

将 Stage 3 生成的代码**自动**部署到目标环境，过程可回滚、可灰度、可追溯。  
**本阶段默认自动执行**，无人工 Gate。

## 二、输入

| 类型 | 来源 | 必填 |
|---|---|---|
| Git commit hash | Stage 3/4/5 完成 | 是 |
| 目标环境 | develop/staging/pre/prod | 是 |
| 部署策略 | 蓝绿/灰度/全量 | 是 |
| DUCC 配置变更 | Stage 2 design | 是 |
| 数据库变更 | Stage 2 design | 是 |

**前置约束**：
- Stage 5 测试通过
- 部署环境为 develop/staging/pre（**生产环境强制走人工**）
- 涉及 DB 变更必须有 DBA 审批（如 DDL）

## 三、Subagent 调度

### 3.1 派发命令

```
task(
  subagent_type: "general",
  description: "部署",
  prompt: "[deployer prompt，见 10-subagent-spec.md §7]"
)
```

### 3.2 工具权限（受限）

| 工具 | 权限 |
|---|---|
| 读 | ✅ |
| 写 | ⚠️ 仅 deploy 类操作 |
| bash | ⚠️ 限制：仅 `git`、`mvn`、`kubectl`、`ssh` |
| MCP（hot_deploy） | ✅ |
| MCP（image_deploy） | ✅ |
| MCP（生产环境） | ❌ |

## 四、部署策略决策

| 环境 | 推荐策略 | 触发 MCP |
|---|---|---|
| develop | hot_deploy | `hot_deploy` |
| staging | hot_deploy 或 image_deploy | 二选一 |
| pre | image_deploy | `image_deploy_from_pod` |
| prod | **人工** + 灰度 | ❌ 不允许 AI 触发 |

### 4.1 hot_deploy vs image_deploy 决策

```
if env == "pre":
    # 预发禁止 hot_deploy（必须是完整镜像）
    use image_deploy
elif env in ["develop", "staging"] and change_is_pure_code:
    use hot_deploy
elif env in ["develop", "staging"] and has_config_or_db_change:
    use image_deploy
```

详细诊断见 `DongBootHotswapTroubleshoot` Skill。

## 五、部署流程

### 5.1 整体流程

```
1. 预检（环境健康、磁盘、内存）
2. DUCC 配置检查/变更
3. DB 变更（如有）
4. 构建镜像/包
5. 备份当前版本
6. 执行部署
7. 健康检查
8. 烟雾测试（关键接口）
9. 流量切换（灰度）
10. 监控观察
11. 标记完成
```

### 5.2 关键 MCP 调用

| 步骤 | MCP | 备注 |
|---|---|---|
| 获取当前应用 | `get_current_app` | 必先调用 |
| 获取 Pod 列表 | `get_pod_list` | 必先调用 |
| 获取变更文件 | `get_changed_files` | - |
| 热部署 | `hot_deploy` | 限定 develop/staging |
| 镜像部署 | `image_deploy_from_pod` | 限定 staging/pre |
| 拉日志 | `list_biz_log_subscriptions` + `get_biz_log` | 部署后验证 |
| R2 回归 | R2 MCP | 部署后验证 |

## 六、预检 Checklist

| 项 | 校验方式 | 失败处理 |
|---|---|---|
| 应用健康 | `get_pod_list` | 中止 |
| 磁盘空间 | DUCC | 中止 |
| 上次部署完成 | 状态查询 | 等待 or 中止 |
| 目标 Pod 可达 | SSH/网络 | 切换 Pod |
| DUCC 配置存在 | 配置查询 | 提示缺失 |
| DB 变更同步 | SQL 检查 | 中止 |

## 七、DB 变更管理

### 7.1 强制规则

- 所有 DDL 必须在 Stage 2 design 中列出
- DDL 必须先在 develop/staging 执行
- pre 环境必须由 DBA 二次确认
- prod DDL 必须有回滚 SQL

### 7.2 自动化

```
1. Scan 设计文档中的 DDL
2. 对比目标 DB 当前 schema
3. 生成 migration SQL
4. 提交变更工单
5. 等审批（人工）
6. 审批通过后执行
```

## 八、DUCC 配置变更

### 8.1 流程

```
1. Scan 设计文档中的 config_key
2. 校验 key 在 DUCC 中已存在（不存在则提示创建）
3. 准备变更 diff
4. 调用 DUCC MCP 更新
5. 触发应用刷新（视配置类型）
```

### 8.2 回滚

- 任何配置变更必须保留上一版本
- 30 分钟内可一键回滚
- 回滚记录写入审计

## 九、灰度策略

### 9.1 灰度比例

| 阶段 | 比例 | 观察时间 |
|---|---|---|
| 阶段 1 | 1% | 10 min |
| 阶段 2 | 10% | 20 min |
| 阶段 3 | 50% | 30 min |
| 阶段 4 | 100% | - |

### 9.2 灰度决策

- 阶段 1 失败 → 自动回滚 + 升级
- 阶段 2/3 失败 → 暂停 + 人工决策
- 阶段 4 失败 → 启动预案回滚

### 9.3 关键指标

- 错误率
- P99 延迟
- 业务核心指标（如订单量、券核销量）

## 十、错误处理

| 错误 | 表现 | 处理 |
|---|---|---|
| 镜像构建失败 | CI 红 | 中止，通知 |
| 部署超时 | 5min 无响应 | 重试 1 次，仍失败回滚 |
| 健康检查失败 | 启动 2min 内 5xx | 自动回滚 |
| 烟雾测试失败 | 关键接口异常 | 自动回滚 |
| 灰度异常 | 错误率 > 阈值 | 自动回滚 |

## 十一、必调用 Skill

| 场景 | Skill |
|---|---|
| Hotswap 失败 | `DongBootHotswapTroubleshoot` |
| 部署后日志 | `DeployBizLogTroubleshoot` |
| 选择部署环境 | `get_current_environment` MCP |

## 十二、产出物

`prd/{feature_id}/06-deploy-record.md`

```markdown
# 部署记录

## 基础信息
- 部署时间：2026-06-05 15:00
- 环境：staging
- 策略：hot_deploy
- 操作人：deployer Subagent
- 变更 ID：DPL-2026-0605-001

## 变更清单
- [x] 业务代码：commit abc123
- [x] DUCC 配置：coupon.enabled = true
- [ ] DB 变更：无

## 执行步骤
1. 预检：✅
2. 配置更新：✅
3. 热部署：✅ (耗时 45s)
4. 健康检查：✅
5. 烟雾测试：✅ (3/3 通过)

## 灰度计划
- 阶段 1 (1%)：15:10
- ...

## 监控观察
（执行后填充）

## 结论
✅ 部署成功，进入 Stage 7
```

## 十三、产出物归档

更新 `meta.json`：

```json
{
  "stage": 6,
  "subagent": "deployer",
  "env": "staging",
  "strategy": "hot_deploy",
  "duration_sec": 240,
  "smoke_test_passed": true,
  "gray_stages": ["1%", "10%", "50%", "100%"],
  "rollback_triggered": false
}
```
