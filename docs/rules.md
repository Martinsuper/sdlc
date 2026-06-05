# Rule Engine

The `sdlc` rule engine enforces coding standards, security policies, and best practices throughout the pipeline. Rules are loaded from YAML files, evaluated by enforcers, and can be temporarily disabled through the exception system.

## Rule Levels

Rules use a 6-level severity system based on RFC 2119:

| Level | Meaning | Default Action |
|-------|---------|----------------|
| `MUST` | Mandatory — violation blocks the pipeline | `block` |
| `MUST_NOT` | Prohibited — violation blocks the pipeline | `block` |
| `SHOULD` | Recommended — violation issues a warning | `warn` |
| `SHOULD_NOT` | Discouraged — violation issues a warning | `warn` |
| `MAY` | Optional — informational only | `warn` |
| `MAY_NOT` | Not recommended — informational | `warn` |

## Enforcers

Four enforcer strategies dispatch rule checks based on the `enforcer` field:

### CREnforcer (`cr`)

Code review enforcer. Scans file contents against regex patterns defined in `rule.pattern`.

- Receives a `files` dict mapping file paths to content strings
- Filters files against `rule.applies_to` glob patterns (supports `**`)
- Reports violations with file path, line number, and message
- Used by: all 9 builtin rule sets

Example rule:
```yaml
- id: no-bare-except
  level: MUST
  category: error-handling
  enforcer: cr
  pattern: "except\\s*:"
  message: "Specify exception type, do not use bare except"
  action: block
  severity: P2
  applies_to: ["**/*.py"]
```

### LintEnforcer (`lint`)

Static lint enforcer. Runs lint tool checks and parses output.

- Receives a `files` list of file objects with `path` and `content`
- Applies `rule.applies_to` filtering and regex pattern matching
- Configurable timeout (default 60s)
- Used for: integration with external linters

### CIEnforcer (`ci`)

CI pipeline enforcer. Checks CI workflow status.

- Receives a `ci_status` dict mapping workflow names to status strings
- Checks workflows listed in `rule.scope.workflows`
- Reports violations for any workflow not in `success` state
- Used for: pipeline integration checks

### RuntimeEnforcer (`runtime`)

Runtime pre/post hook enforcer. Runs check scripts and inspects runtime data.

- Receives a `runtime` dict with check results
- Evaluates checks listed in `rule.scope.checks`
- Reports violations for truthy check values
- Used for: runtime validation hooks

## Rule Sets

9 built-in rule sets, each containing 3 rules (27 total):

### coding-must

| ID | Level | Category | Description |
|----|-------|----------|-------------|
| `no-thread-sleep` | MUST | coding | Block `Thread.sleep` in Java |
| `no-system-out` | SHOULD | logging | Use logging framework instead of `System.out/err` |
| `no-hardcoded-secrets` | MUST | security | Block hardcoded passwords and API keys |

### python-must

| ID | Level | Category | Description |
|----|-------|----------|-------------|
| `no-bare-except` | MUST | error-handling | Block bare `except:` clauses |
| `no-eval` | MUST | security | Block `eval()` usage |
| *(1 more)* | | | |

### node-must

| ID | Level | Category | Description |
|----|-------|----------|-------------|
| `no-console-log` | SHOULD | logging | Use logging framework instead of `console.log` |
| `no-sync-fs` | MUST | performance | Block synchronous file operations |
| *(1 more)* | | | |

### go-must

| ID | Level | Category | Description |
|----|-------|----------|-------------|
| `no-panic-in-lib` | MUST | error-handling | Block `panic()` in library code |
| `must-check-error` | MUST | error-handling | Require error return value checks |
| *(1 more)* | | | |

### rust-must

| ID | Level | Category | Description |
|----|-------|----------|-------------|
| `no-unwrap-in-prod` | MUST | error-handling | Block `unwrap()` in production code |
| `no-unsafe` | MUST | safety | Block `unsafe` blocks |
| *(1 more)* | | | |

### frontend-must

| ID | Level | Category | Description |
|----|-------|----------|-------------|
| `no-inline-styles` | SHOULD | styling | Use CSS classes instead of inline styles |
| `no-direct-dom-access` | MUST | framework | Block direct DOM manipulation |
| *(1 more)* | | | |

### mobile-must

| ID | Level | Category | Description |
|----|-------|----------|-------------|
| `no-hardcoded-urls` | MUST | security | Block hardcoded API URLs |
| `no-main-thread-io` | MUST | performance | Block IO on main thread |
| *(1 more)* | | | |

### data-must

| ID | Level | Category | Description |
|----|-------|----------|-------------|
| `no-collect-action` | MUST | performance | Block `collect()` that pulls all data to driver |
| `no-shuffle-without-partition` | SHOULD | performance | Require partition count in shuffle operations |
| *(1 more)* | | | |

### infra-must

| ID | Level | Category | Description |
|----|-------|----------|-------------|
| `no-hardcoded-ips` | MUST | security | Block hardcoded IP addresses |
| `no-latest-tag` | MUST | reliability | Block `:latest` image tags |
| *(1 more)* | | | |

## Exception Management

Rules can be temporarily disabled through the `ExceptionManager`:

```python
from sdlc.rule.exceptions import ExceptionManager
from sdlc.rule.models import RuleException

manager = ExceptionManager()

# Grant an exception
exc = RuleException(
    id="exc-1",
    rule_id="no-console-log",
    reason="Debug sprint — temporary exemption",
    granted_by="team-lead",
    granted_at="2026-06-05T00:00:00Z",
    expires_at="2026-07-01T00:00:00Z",
    scope={"files": ["src/debug/**"]},
    auto_renew=False,
)
manager.add(exc)

# Check if a rule has an active exception
active = manager.is_active("no-console-log", context={"files": ["src/debug/logger.ts"]})

# Find expiring exceptions
expiring = manager.expiring_soon(days=3)

# Find expired exceptions
expired = manager.expire_check()

# Remove an exception
manager.remove("exc-1")
```

### Exception Properties

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique exception identifier |
| `rule_id` | str | The rule being exempted |
| `reason` | str | Justification for the exemption |
| `granted_by` | str | Who approved the exemption |
| `granted_at` | str | ISO timestamp when granted |
| `expires_at` | str | ISO timestamp when exemption ends |
| `scope` | dict | File/stage patterns where exemption applies |
| `auto_renew` | bool | Whether to auto-renew on expiry |

### Scope Matching

The `scope` field filters where an exception applies. Keys are context dimensions (e.g., `files`, `stages`) with glob pattern lists:

```yaml
scope:
  files: ["src/legacy/**/*.java"]
  stages: ["s-impl-backend"]
```

An exception matches when **all** scope dimensions match the current context. If a dimension is absent from the scope, it applies broadly for that dimension.

## CLI Commands

```bash
# List rules
sdlc rule list
sdlc rule list --category security
sdlc rule list --level MUST

# Disable a rule
sdlc rule disable <rule-id> --until 2026-07-01 --reason "Debug sprint"

# Re-enable a rule
sdlc rule enable <rule-id>

# Check rules for a stage
sdlc rule check --stage s-impl-backend
```

## Adding Custom Rules

### 1. Create a YAML file

```yaml
# my-rules.yaml
- id: my-custom-rule
  level: MUST
  category: security
  description: "Block usage of deprecated API"
  enforcer: cr
  pattern: "DeprecatedApi\\.call\\("
  message: "DeprecatedApi is removed in v3.0, use NewApi instead"
  action: block
  severity: P1
  applies_to: ["**/*.py", "**/*.java"]
  scope:
    stages: ["s-impl-backend", "s-impl-frontend"]
    adapters: ["python-fastapi", "jd-spring-boot"]
  references: ["https://wiki/internal/deprecated-api-migration"]
```

### 2. Load the rule set

Place YAML files in `doc/kb/rules/` or load them programmatically:

```python
from sdlc.rule.engine import RuleEngine
from pathlib import Path

engine = RuleEngine()
count = engine.load_from_yaml(Path("my-rules.yaml"))
```

### 3. Query rules

```python
# All rules for a stage
rules = engine.for_stage("s-impl-backend")

# All rules for an adapter
rules = engine.for_adapter("python-fastapi")

# All rules for a subagent role
rules = engine.for_role("coder")  # coding, error-handling, performance, concurrency

# Filter by category and level
rules = engine.list_rules(category="security", level=RuleLevel.MUST)
```

### 4. Check rules

```python
# Check a single rule
violations = engine.check("my-custom-rule", context={
    "files": {"src/api.py": "DeprecatedApi.call()"},
})

# Check all rules for a stage
violations = engine.check_all("s-impl-backend", context={
    "files": {"src/api.py": "DeprecatedApi.call()"},
    "ci_status": {"build": "success", "test": "failed"},
})
```

## Integration with Gates

Quality gates can block pipelines based on rule violations:

- `GateTrigger.ON_RULE_VIOLATION` triggers a gate when violations of a minimum level are detected
- `block_conditions.on_must_violation` blocks the pipeline if any `MUST`-level rule is violated
- Violation context is passed to gate evaluation for decision-making