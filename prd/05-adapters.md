# 05. 适配器 (v2.0)

> **Adapter = 把"只在某技术栈下有效"的能力封装起来**  
> 主流程零技术栈知识；新增技术栈 = 新增 Adapter（不破坏主流程）

---

## 一、Adapter 总览

| ID | 语言/框架 | 状态 | 备注 |
|---|---|---|---|
| `dongboot` | Java / DongBoot | 完整 | 含全 JD 中间件生态 |
| `spring-boot` | Java / Spring Boot | 完整 | 标准 Spring |
| `python-flask` | Python / Flask | 完整 | |
| `python-django` | Python / Django | 完整 | |
| `python-fastapi` | Python / FastAPI | 完整 | |
| `node-express` | Node.js / Express | 完整 | |
| `node-nest` | Node.js / NestJS | 完整 | |
| `frontend-react` | TypeScript / React | 完整 | |
| `frontend-vue` | TypeScript / Vue | 完整 | |
| `go-gin` | Go / Gin | 完整 | |
| `go-kratos` | Go / Kratos | 完整 | |
| `mobile-android` | Kotlin / Android | 完整 | |
| `mobile-ios` | Swift / iOS | 完整 | |
| `mobile-flutter` | Dart / Flutter | 完整 | |
| `infra-terraform` | HCL | 完整 | |
| `infra-helm` | YAML | 完整 | |
| `data-spark` | Scala/PySpark | 完整 | |
| `library-publish` | 任意 | 完整 | 纯 SDK/库发布 |
| `no-tech` | 文档/配置 | 完整 | 不涉及代码 |

总计 **18 个**内置 Adapter。新增 Adapter = 写一份 YAML/JSON 配置 + (可选) 一些胶水脚本。

---

## 二、Adapter Schema

```yaml
id: string                      # 唯一标识，kebab-case
name: string                    # 展示名
language: enum                  # java | go | python | node | ts | rust | kotlin | swift | dart | scala | ...
framework: string?              # dongboot | spring-boot | flask | ...
version: string                 # adapter 自身版本
description: string

detection:                      # 自动检测
  priority: int                 # 多 adapter 冲突时优先级（数字越大越优先）
  file_globs: [string]
  package_patterns: [string]
  import_patterns: [string]
  shebang: string?              # 如 #!/usr/bin/env python3

stages:                         # 覆盖默认 stage 行为
  - stage_id: string
    subagent: string?
    prompt_template: string?
    extra_inputs: [artifact_type]?
    extra_outputs: [artifact_type]?
    post_actions: [action]?
    pre_actions: [action]?
    tool_overrides: map?        # 工具覆盖

components:                     # 推荐/强制使用的技术栈组件
  cache: enum?
  http: enum?
  lock: enum?
  log: enum?
  threadpool: enum?
  database: enum?
  test_framework: enum?
  sequence: enum?
  schedule: enum?
  message_queue: enum?
  search: enum?
  monitor: enum?

build:
  command: string
  artifact_pattern: string
  artifact_path_in_workspace: string?

test:
  command: string
  unit_test_command: string?
  integration_test_command: string?
  coverage_command: string?
  coverage_threshold: float?    # 0.0-1.0

lint:
  command: string?
  config_file: string?

deploy:
  command: string?
  hot_deploy_command: string?
  image_deploy_command: string?
  env_strategies:               # 不同环境策略
    develop: enum               # hot_deploy | image_deploy | manual
    staging: enum
    pre: enum
    prod: enum

runtime:
  startup_command: string?
  health_check: string?         # /actuator/health 之类
  graceful_shutdown_signal: string?

conventions:                    # 代码/产物规范
  file_header: string?          # 锚点注释模板
  test_naming: string?          # e.g. *Test.java, *_test.py, *.spec.ts
  test_location: string?        # src/test/java, tests/, __tests__/
  code_naming: string?
  package_layout: string?       # controller/service/dao 分层

quality_gates:                  # 强制质量门
  - name: lint
    command: string
    blocking: bool
  - name: unit-test
    command: string
    blocking: bool
  - name: coverage
    threshold: float
    blocking: bool
  - name: security-scan
    command: string?
    blocking: bool

mcp_tools:                      # 关联的 MCP 工具
  - name: string                # dongboot_analyzer
    when: string?               # 触发条件
    fallback: string?           # 失败时降级

# v2.2 新增：规则/规范强制
enforce_rules: bool?            # 默认 true
rule_sets:                      # 该 adapter 启用的规则集
  - string                      # doc/kb/rules/MUST.yaml
rule_overrides:                 # 临时豁免（带过期）
  - id: string                  # 规则 ID
    enabled: bool
    reason: string
    expires_at: date
    approver: string

# v2.2 新增：必加载的 KB
required_kb:
  - string                      # doc/kb/architecture/component-catalog.md
  - string                      # doc/kb/standards/coding-style.md
```

---

## 三、详细示例：DongBoot Adapter

```yaml
id: dongboot
name: 企业 DongBoot 框架
language: java
framework: Spring Boot (DongBoot 扩展)
version: "2.0"

detection:
  priority: 100                 # 比 spring-boot 优先
  file_globs:
    - "**/pom.xml"
  package_patterns:
    - "com.jd.**.dongboot.*"
    - "com.jd.**.controller.DongBootApplication"
  import_patterns:
    - "com.jd.dongboot"
    - "com.jd.donglog"
    - "com.jd.dongdal"
    - "com.jd.dongthread"
    - "com.jd.dongcache"
    - "com.jd.donghttp"
    - "com.jd.donglock"
    - "com.jd.sequence"
    - "com.jd.internal-mq"

stages:
  - stage_id: implement-backend
    subagent: coder-jvm-dongboot
    prompt_template: prompts/implement-backend-dongboot.md
    extra_outputs: [dongboot_anchors, donglog_audit]
    pre_actions:
      - kind: mcp
        spec:
          tool: dongboot_analyzer.check_dongboot_status
          required: true
    post_actions:
      - kind: skill
        spec:
          skill: MultiSkillCoordination
          reason: 业务改动触发多个 dongboot 子 skill
      - kind: mcp
        spec:
          tool: dongboot_analyzer.scan_component_usage
      - kind: mcp
        spec:
          tool: dongboot_analyzer.check_required_anchors
  - stage_id: cr
    subagent: reviewer-jvm-dongboot
    extra_inputs: [dongboot_anchors]
  - stage_id: monitor-setup
    subagent: sre-writer-jvm-dongboot
    skill: DongMonitorDashboard
    extra_outputs: [donglog_template, dongmonitor_config]

components:
  cache: dongcache               # 强制
  http: donghttp
  lock: donglock
  log: donglog_biz
  threadpool: dongthread
  database: dongdal
  test_framework: dongmock
  sequence: dongsequence
  schedule: dongschedule
  message_queue: internal-mq
  search: donges                 # ES
  monitor: dongmonitor

build:
  command: mvn -DskipTests package
  artifact_pattern: "target/*.jar"
  artifact_path_in_workspace: "target/{artifactId}-{version}.jar"

test:
  command: mvn test
  unit_test_command: mvn test -Dtest='*Test'
  integration_test_command: mvn test -Dtest='*IT'
  coverage_command: mvn test jacoco:report
  coverage_threshold: 0.8

lint:
  command: mvn checkstyle:check
  config_file: checkstyle.xml

deploy:
  hot_deploy_command: "dongboothotserver:hot_deploy"
  image_deploy_command: "image_deploy_from_pod"
  env_strategies:
    develop: hot_deploy          # 开发环境热部署
    staging: image_deploy
    pre: image_deploy
    prod: manual                 # 人工

runtime:
  startup_command: "java -classpath '.:lib/*' ${main_class}"
  health_check: "/actuator/health"
  graceful_shutdown_signal: "TERM"

conventions:
  file_header: |
    /**
     * @sdlc-feature {feature_id}
     * @sdlc-stage {stage_id}
     * @sdlc-requirement {requirement_id}
     * @sdlc-adr {adr_id}
     * @sdlc-generated-by {subagent_id}
     * @sdlc-timestamp {ts}
     */
  test_naming: "*Test.java"
  test_location: "src/test/java"
  code_naming: "UpperCamelCase.java"
  package_layout: "controller / service / dao / model / config"

quality_gates:
  - name: lint
    command: mvn checkstyle:check
    blocking: true
  - name: unit-test
    command: mvn test
    blocking: true
  - name: coverage
    threshold: 0.8
    blocking: true
  - name: security-scan
    command: "mvn org.owasp:dependency-check-maven:check"
    blocking: true

mcp_tools:
  - name: dongboot_analyzer
    when: stage == "implement-backend"
  - name: dongboothotserver
    when: stage == "deploy"
  - name: recommend_dongboot_version
    when: stage == "package" or stage == "deploy"
  - name: internal-rpctimeout
    when: stage == "design" or stage == "implement-backend"
```

---

## 四、其他 Adapter 简表

### 4.1 Spring Boot Adapter

```yaml
id: spring-boot
name: Spring Boot（标准）
language: java
framework: Spring Boot
detection:
  priority: 50                  # 比 dongboot 低
  file_globs: ["**/pom.xml", "**/build.gradle*"]
  import_patterns: ["org.springframework.boot"]

stages:
  - stage_id: implement-backend
    subagent: coder-jvm-spring

components:
  cache: caffeine                # 或 redis
  http: feign
  log: slf4j
  threadpool: executors
  database: jdbc
  test_framework: junit
  message_queue: rabbitmq       # 或 kafka
  monitor: micrometer

build:
  command: mvn -DskipTests package
  artifact_pattern: "target/*.jar"

deploy:
  env_strategies:
    prod: image_deploy

quality_gates:
  - {name: lint, blocking: true}
  - {name: unit-test, blocking: true}
  - {name: coverage, threshold: 0.7, blocking: true}
```

### 4.2 Python Flask Adapter

```yaml
id: python-flask
name: Python Flask
language: python
framework: Flask
detection:
  file_globs: ["**/requirements.txt", "**/pyproject.toml", "**/Pipfile"]
  import_patterns: ["flask"]
  shebang: "#!/usr/bin/env python3"

stages:
  - stage_id: implement-backend
    subagent: coder-python-flask
  - stage_id: unit-test
    subagent: tester-python
    subagent_overrides:
      framework: pytest

components:
  cache: redis
  http: requests
  log: loguru
  database: sqlalchemy
  test_framework: pytest

build:
  command: "python -m build"
  artifact_pattern: "dist/*.whl"

test:
  command: "pytest"
  coverage_command: "pytest --cov=src --cov-report=html"
  coverage_threshold: 0.75

deploy:
  command: "docker build -t {image} . && docker push {image}"
  env_strategies:
    prod: image_deploy

conventions:
  file_header: |
    # @sdlc-feature {feature_id}
    # @sdlc-stage {stage_id}
    # @sdlc-requirement {requirement_id}
    # @sdlc-generated-by {subagent_id}
    # @sdlc-timestamp {ts}
  test_naming: "test_*.py"
  test_location: "tests/"
  code_naming: "snake_case.py"
```

### 4.3 Node Express Adapter

```yaml
id: node-express
language: javascript
framework: Express
detection:
  file_globs: ["**/package.json"]
  import_patterns: ["express"]

stages:
  - stage_id: implement-backend
    subagent: coder-nodejs
  - stage_id: unit-test
    subagent: tester-nodejs

components:
  cache: redis
  http: axios
  log: winston
  database: prisma
  test_framework: jest

build:
  command: "npm run build"
  artifact_pattern: "dist/**/*.js"

test:
  command: "npm test"
  coverage_command: "npm test -- --coverage"
  coverage_threshold: 0.7
```

### 4.4 Frontend React Adapter

```yaml
id: frontend-react
language: typescript
framework: React
detection:
  file_globs: ["**/package.json"]
  import_patterns: ["react", "react-dom"]

stages:
  - stage_id: implement-frontend
    subagent: coder-frontend-react
  - stage_id: unit-test
    subagent: tester-frontend
  - stage_id: e2e-test
    subagent: tester-e2e-playwright

components:
  state: redux
  http: axios
  test_framework: jest
  e2e: playwright

build:
  command: "npm run build"
  artifact_pattern: "build/**/*"

deploy:
  command: "aws s3 sync build/ s3://{bucket}"
  env_strategies:
    prod: image_deploy            # 或 static_deploy
```

### 4.5 Go Gin Adapter

```yaml
id: go-gin
language: go
framework: Gin
detection:
  file_globs: ["**/go.mod"]
  import_patterns: ["github.com/gin-gonic/gin"]

stages:
  - stage_id: implement-backend
    subagent: coder-go-gin

components:
  cache: redis
  http: net/http
  log: zap
  database: gorm
  test_framework: testify

build:
  command: "go build -o bin/app ./cmd"
  artifact_pattern: "bin/app"

test:
  command: "go test ./..."
  coverage_command: "go test -cover ./..."
  coverage_threshold: 0.7
```

---

## 五、Adapter 自动检测算法

```python
def detect_adapter(workspace_path: str) -> Optional[Adapter]:
    candidates = []
    for adapter in ADAPTER_REGISTRY:
        score = 0
        # 文件匹配
        for glob in adapter.detection.file_globs:
            if any_file_matches(workspace_path, glob):
                score += 10
        # 导入匹配
        for pattern in adapter.detection.import_patterns:
            if any_file_contains(workspace_path, pattern):
                score += 5
        # shebang
        if adapter.detection.shebang and has_shebang(workspace_path, adapter.detection.shebang):
            score += 3
        if score > 0:
            candidates.append((score, adapter.detection.priority, adapter))
    
    if not candidates:
        return None
    
    # 排序：score 优先，priority 兜底
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][2]
```

**多 Adapter 场景**（如 monorepo）：
- 用 `workspace_subdir` 指定子目录
- 各子目录独立检测

---

## 六、新增 Adapter 流程

### 6.1 零代码方式（推荐）

```yaml
# 在 ~/.claude/adapters/my-tech.yaml 写一份配置
# 重新加载即可
```

### 6.2 复杂 Adapter（带胶水脚本）

```python
# 在 ~/.claude/adapters/my-tech/
#   - adapter.yaml
#   - prompts/...
#   - scripts/post_impl.py
#   - templates/file_header.template
```

主流程通过 `subagent` + `prompt_template` + `post_actions` 字段调用。

---

## 七、Adapter 与 Skill 的关系

**Adapter 定义"做什么"（技术栈特定）**  
**Skill 提供"怎么用工具"（MCP 工具/Skill 工具）**

例如 DongBoot Adapter：
- Adapter 规定 implement-backend 要用 DongCache、DongLog、DongThread 等组件
- Skill `DongCache` / `DongLog` / `DongThread` 提供具体接入代码模板

**调用流程**：
```
Subagent coder-jvm-dongboot
  → 读 Adapter.dongboot.components
  → 触发 Skill MultiSkillCoordination
    → 同轮触发 DongLog + DongCache + DongThread + ...
      → 各自产出代码片段
    → 合并为最终 diff
```

---

## 八、Adapter 的测试

每个 Adapter 自带 contract test：
- 给定一个简单需求，Adapter 生成的产物应该包含所有 `components` 字段
- Adapter 的 `quality_gates` 必须在 CI 跑通
- Adapter 的 `detection` 必须在示例工程上识别成功

详见 `/tests/adapters/{id}_test.py`。

---

## 九、版本

- v2.0 (2026-06-05): 18 Adapter 完整 Schema + DongBoot 详细实现
- v2.2 (2026-06-05): Adapter Schema 新增 `enforce_rules` / `rule_sets` / `rule_overrides` / `required_kb` 字段，详见 `15-rule-and-standard-library.md`

- v2.0 (2026-06-05): 18+ Adapter 库（DongBoot 降为众多 adapter 之一）
