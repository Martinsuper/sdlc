# 04 - Stage 3 编码（含单测骨架）

## 一、目标

基于 Stage 2 的设计方案，**自动生成可运行的业务代码 + 单测骨架**。  
本阶段不追求 100% 覆盖率，而是产出**结构正确、可被 Stage 5 增强**的代码。

## 二、输入

| 类型 | 来源 | 必填 |
|---|---|---|
| `02-design/` 全套 | Stage 2 | 是 |
| 项目工程根目录 | - | 是 |
| 团队代码规范 | `~/.claude/rules/coding-style.md` | 否 |
| DongBoot 组件规范 | Skill 内置 | 是（自动加载） |

**前置约束**：
- Stage 2 必须通过 Gate 2
- 工程必须是 DongBoot 接入状态
- 已 `mvn compile` 通过

## 三、Subagent 调度策略

### 3.1 并行模型

编码阶段根据模块依赖关系，**并行派发 2~4 个 coder-backend Subagent**：

```
                 ┌─→ coder-A (coupon-service 业务逻辑)
architect ──→ ──┼─→ coder-B (coupon-dao 持久层)
                 └─→ coder-C (coupon-api Facade)
                 
（coder-A 依赖 B、C；B/C 可并行）
```

### 3.2 派发命令

```
# 并行派发
task(subagent_type="general", description="编码-persistent", prompt="...")
task(subagent_type="general", description="编码-api", prompt="...")
# 等 B/C 完成后
task(subagent_type="general", description="编码-service", prompt="...")
```

### 3.3 Subagent 间的握手

每个 Subagent 完成时：
1. 写入 `prd/{feature_id}/03-code/{module}/HANDOFF.md`
2. 主对话读取 HANDOFF 后再派发下一个 Subagent

## 四、产物清单

输出目录：`prd/{feature_id}/03-code/{module}/`

```
03-code/
├── coupon-api/
│   ├── src/main/java/.../CouponQueryService.java
│   ├── src/main/java/.../dto/...
│   ├── HANDOFF.md
├── coupon-dao/
│   ├── src/main/java/.../CouponDao.java
│   ├── src/main/java/.../CouponEntity.java
│   ├── src/main/resources/mapper/CouponMapper.xml
│   ├── HANDOFF.md
├── coupon-service/
│   ├── src/main/java/.../impl/CouponServiceImpl.java
│   ├── src/main/java/.../biz/CouponBiz.java
│   ├── HANDOFF.md
├── coupon-task/
│   ├── src/main/java/.../job/CouponExpireJob.java
│   ├── HANDOFF.md
└── meta.json
```

每个 Java 文件头部必须包含锚点注释：

```java
/**
 * @sdlc-feature {feature_id}
 * @sdlc-stage 3
 * @sdlc-requirement US-001, US-002
 * @sdlc-adr ADR-002
 * @sdlc-generated-by coder-backend v1.0
 * @sdlc-timestamp {ISO8601}
 */
public class CouponServiceImpl implements CouponQueryService {
    // ...
}
```

## 五、代码生成规范

### 5.1 命名

| 元素 | 规范 | 示例 |
|---|---|---|
| 类 | UpperCamelCase | `CouponServiceImpl` |
| 方法 | lowerCamelCase | `queryAvailableCoupons` |
| 变量 | lowerCamelCase | `couponList` |
| 常量 | UPPER_SNAKE | `MAX_COUPON_PER_USER` |
| 包 | 全小写 | `com.jd.coupon.service.impl` |

### 5.2 注释

- 类级：必须含 `@sdlc-*` 锚点
- 公开方法：必须含 Javadoc
- 复杂逻辑：行内注释解释"为什么"
- 禁止：`// TODO`（除非 Stage 3 明确产出 TODO 清单）

### 5.3 错误处理

```java
// 推荐
public Result<CouponDTO> useCoupon(UseCouponRequest request) {
    if (request == null) {
        return Result.fail(ErrorCode.PARAM_INVALID, "请求不能为空");
    }
    try {
        return bizLogic(request);
    } catch (BusinessException e) {
        BizLogger.warn("biz.error", "useCoupon failed", e, "userId", request.getUserId());
        return Result.fail(e.getErrorCode(), e.getMessage());
    } catch (Exception e) {
        BizLogger.error("biz.error", "useCoupon system error", e, "userId", request.getUserId());
        return Result.fail(ErrorCode.SYSTEM_ERROR, "系统繁忙");
    }
}
```

### 5.4 DongBoot 组件使用

**强制要求**：所有原生写法必须替换为 DongBoot 组件。详见各组件 Skill。

| 场景 | 禁止 | 推荐 |
|---|---|---|
| 缓存 | GuavaCache | DongCache（基于 Guava 包装） |
| HTTP | OkHttpClient | DongHttp |
| 线程池 | ThreadPoolExecutor | DongThread |
| 锁 | Redis SETNX | DongLock |
| 分布式 ID | Snowflake 手写 | DongSequence |
| 分布式调度 | Quartz | DongSchedule |
| 数据库 | JdbcTemplate | DongDAL |
| 日志 | System.out / log4j | DongLog + BizLogger |

### 5.5 单测骨架生成

每个 Service/Manager 类必须配套生成 `*Test.java` 骨架：

```java
@ExtendWith(SpringExtension.class)
@SpringBootTest(classes = Application.class)
public class CouponServiceImplTest {
    @MockBean
    private CouponDao couponDao;
    @Autowired
    private CouponServiceImpl couponService;
    
    @Test
    public void testUseCoupon_Success() {
        // TODO[Stage 5]: 补充完整业务断言
        // 当前仅骨架，Stage 5 跑 R2 生成
    }
    
    @Test
    public void testUseCoupon_CouponNotExist() {
        // TODO[Stage 5]
    }
    
    @Test
    public void testUseCoupon_AlreadyUsed() {
        // TODO[Stage 5]
    }
}
```

## 六、Subagent 内部工作流

```
1. Read 02-design/ 全套
2. Scan 工程根（pom.xml、目录结构）
3. Locate 目标模块（新增 or 复用）
4. Generate DTO/VO 类（基于 API 契约）
5. Generate Entity + Mapper（基于 DB 设计）
6. Generate Dao / Repository（基于 DongDAL）
7. Generate Service 接口（基于 API 契约）
8. Generate ServiceImpl（含 BizLogger 接入）
9. Generate Controller / Facade
10. Generate 单测骨架（含 TODO 标记给 Stage 5）
11. Run mvn compile（确保编译通过）
12. Write HANDOFF.md
13. 通知主对话
```

## 七、与现有 Skill 的协同

每个 Subagent **必须**按需触发以下 Skill（详见 `MultiSkillCoordination`）：

| 触发条件 | 调用的 Skill |
|---|---|
| 涉及缓存 | DongCache |
| 涉及 HTTP | DongHttp |
| 涉及线程池 | DongThread |
| 涉及锁 | DongLock |
| 涉及 ID 生成 | DongSequence |
| 涉及定时任务 | DongSchedule |
| 涉及 DB | DongDAL |
| 涉及 ES | DongES |
| 涉及 MQ | internal-mq |
| 业务代码 | DongLog（BizLogger 接入） |
| 已有 internal-rpc | internal-rpc（超时/限流） |

**多 Skill 协同**：在同一轮中触发所有匹配项（详见 MultiSkillCoordination §0）。

## 八、验证机制

### 8.1 自动验证（Stage 3 内部）

```bash
# Subagent 必须执行
mvn clean compile -DskipTests
mvn checkstyle:check
mvn pmd:check
```

任意失败则 Subagent 自我修复（最多 3 轮），仍失败则升级到 D 类。

### 8.2 产物清单校验

主对话在 Subagent 完成后，校验：

- [ ] 所有 ADR 中提到的类都已生成
- [ ] 所有 API 方法都有实现
- [ ] 所有 DB 表都有 Entity + Mapper
- [ ] 所有 Service 都有单测骨架
- [ ] BizLogger 至少 1 个关键方法已接入
- [ ] `mvn compile` 通过

## 九、错误处理

| 异常 | 处理 |
|---|---|
| `mvn compile` 失败 | 自动修复 → 仍失败回退到 Stage 2 |
| 设计方案不完整 | 回退 Stage 2 补充 |
| DongBoot 组件未识别 | 调用 `DongBootIntegration` 自检 |
| 循环依赖 | 派发新 Subagent 重构依赖图 |

## 十、产出物归档

更新 `meta.json`：

```json
{
  "stage": 3,
  "subagent": "coder-backend",
  "subagents_count": 3,
  "files_generated": 42,
  "lines_generated": 3580,
  "compile_status": "success",
  "coverage_skeleton": "100%",
  "modules": ["coupon-api", "coupon-dao", "coupon-service", "coupon-task"]
}
```
