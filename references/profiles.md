# 项目画像探测与章节裁剪

> 被 design / review / deploy 等阶段引用。目的：让通用项目拿到干净的产出，而不是被迫在一堆企业内部专有章节里填"不涉及"。

进入实质阶段前跑一次这套探测，得出两样东西：**项目画像（profile）** 和 **启用的章节标签集合（tags）**。后续模板/checklist 据此裁剪。

---

## 一、探测项目画像

看项目根的信号文件，推断画像。优先读文件真实存在性，不要凭项目名猜。

| 信号 | 推断画像 |
| --- | --- |
| `pom.xml` / `build.gradle` / `build.gradle.kts` | `backend-service`（JVM） |
| `package.json` 且含 react/vue/next/svelte/angular 依赖 | `web-frontend` |
| `package.json` 且含 express/koa/nestjs/fastify，无前端框架 | `backend-service`（Node） |
| `go.mod` | `backend-service`（Go） |
| `requirements.txt` / `pyproject.toml` / `setup.py` 且有 web 框架(flask/django/fastapi) | `backend-service`（Python） |
| `pyproject.toml` / `setup.py` 且有 `[console_scripts]` 或 CLI 入口，无 web 框架 | `cli-library` |
| `Cargo.toml` | 有 `[[bin]]` → `cli-library`；否则 `backend-service`（Rust） |
| 无任何 web 框架依赖、以 `main`/lib 入口为主 | `cli-library` |
| 顶层有 OSS LICENSE + `CONTRIBUTING.md` + 无公司内部私有依赖 | 叠加 `oss-generic` 特征（影响 [enterprise-infra] 默认关闭） |

**探测方法**：用 `ls`/`find` 看信号文件，必要时读 `package.json`/`pyproject.toml`/`pom.xml` 的依赖段确认。一个项目可能是复合画像（如 full-stack = backend + frontend），此时两组标签都启用。

**探测不了或有歧义**（如 monorepo、看不出主技术栈）→ 直接问用户一句：「这个项目主要是后端服务 / 前端应用 / CLI 或库 / 其它？涉不涉及数据库、缓存、消息队列？」不要硬猜。

---

## 二、章节标签与启用条件

模板和 checklist 里每个"可能不适用"的章节都打了标签。按下表决定启用哪些。**未启用的章节直接不出现在产出里**（而不是留"不涉及"占位），保持产出干净。

| 标签 | 启用条件 | 涉及的模板章节 |
| --- | --- | --- |
| `[db]` | 探测到 ORM/SQL/数据库客户端依赖（mybatis/jpa/gorm/sqlalchemy/prisma/sqlx 等），或用户确认涉及数据库 | 数据库设计、SQL 清单、数据量评估 |
| `[cache]` | 探测到 redis/memcached 客户端，或用户确认 | 缓存设计、大 key、缓存降级 |
| `[mq]` | 探测到 kafka/rabbitmq/pulsar/rocketmq/云 MQ 客户端，或用户确认 | 异步消息、消息体兼容、消费异常 |
| `[job]` | 探测到定时任务框架（quartz/xxl-job/celery/cron 封装），或用户确认 | 定时任务设计 |
| `[frontend-compat]` | 画像含 `web-frontend` | 浏览器/端兼容、埋点、性能预算 |
| `[jvm-runtime]` | 画像为 JVM 后端 | JVM 内存/GC 类监控与上线检查项 |
| `[enterprise-infra]` | **默认关闭**。仅当项目显式挂载企业规范 overlay 时启用 | 企业内部专有：内部 SQL 校验工具、内部监控体系(如 internal-monitoring)、内部 RPC 框架实例数(如 internal-rpc)、内部配置中心特定项、数仓/BI 影响、内部网关等 |

---

## 二·五、overlay 加载（企业规范包）

`[enterprise-infra]` 的开关由 overlay 机制控制。探测标签后，检查项目是否挂载了 overlay：

1. **读 `.sdlc/overlay.yaml`**（项目级配置，不是阶段产物，status 不扫描它）：
   ```yaml
   name: my-enterprise          # 指向 overlays/<name>/
   enable_tags: [enterprise-infra]
   ```
2. **无此文件** → 只用通用基座，`[enterprise-infra]` 保持关闭。这是默认路径。
3. **有此文件** → 按 `name` 找到 skill 内 `overlays/<name>/`：
   - 启用 `enable_tags` 声明的标签（通常含 `[enterprise-infra]`）。
   - 加载 `overlays/<name>/sections.md`：把每个片段按其 `@after` 标记，插入通用 design 产出的对应基座章节之后；片段用独立 `E{n}` 编号段，不与基座数字段冲突。
   - 加载 `overlays/<name>/checklist.md`：把 `@stage: review` 项追加到评审维度，`@stage: deploy` 项追加到上线检查清单。
4. **异常处理**：
   - `name` 指向的包不存在 → 警告并降级为纯通用基座，提示"overlay X 未找到，用通用产出"。
   - 多个片段用了相同 `@id` → 报冲突要求改名，不静默覆盖。

> 已内置 overlay：`my-enterprise`（企业内部内部规范，含 internal-sql-checker/存储加密/配送主流程/internal-mq-client/internal-monitoring/internal-gateway等）。项目要用时在 `.sdlc/overlay.yaml` 写 `name: my-enterprise` 即可。

---

## 三、企业内部专有项的通用化映射

旧模板里大量企业内部内部概念，一律泛化为通用表述。默认产出用通用表述；只有启用 `[enterprise-infra]` 时才补充内部专有项。

| 旧的内部专有表述 | 通用化后的表述 |
| --- | --- |
| internal-sql-checker SQL 校验 | SQL 经语法/规范校验（如 sqlfluff、或团队内部工具） |
| 存储加密（企业加密方案/长度工具/枚举变更 SOP） | 敏感字段加密（按团队安全规范），默认剔除具体内部工具 |
| internal-monitoring 存活/异常监控 | 健康探针 / 错误率 / P99 延迟 |
| internal-rpc 在线实例数 | 服务实例数（如涉及注册中心） |
| internal-mq / internal-mq-client / internal-mq-client 消费 | 消息队列消费情况（`[mq]` 控制，客户端按团队技术栈） |
| Apollo 动态配置 | 配置中心（Apollo / Nacos / 云配置服务） |
| Jimdb / JED | 缓存 / 存储服务（`[cache]` 控制） |
| internal-gateway、城市配置后台、配送主流程 | 归入 `[enterprise-infra]`，默认剔除 |
| 钱相关逻辑（计费/运费/补贴/抽佣/对账）、单号逻辑 | 归入 `[enterprise-infra]`，默认剔除（通用项目按普通业务逻辑处理） |
| BI / 数仓影响 | 归入 `[enterprise-infra]`，默认剔除 |
| 双机房流量、NP 挂载 | 多可用区流量对等 / 存储挂载（如涉及） |

---

## 四、输出

探测完成后，向用户简报一行结论，让裁剪对用户透明，例如：

```
📐 项目画像：backend-service (Python/FastAPI)
   启用章节：[db] [cache]  ｜ 剔除：[mq] [job] [frontend-compat] [enterprise-infra]
```

然后带着这套标签进入具体阶段。阶段提示词会引用这里得出的 profile 和 tags。
