# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.3.x   | Yes       |
| 0.2.x   | Yes       |
| 0.1.x   | No        |
| < 0.1   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in `sdlc`, please report it responsibly:

1. **Do not** file a public issue.
2. Email the security team at **security@sdlc.dev** with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. You will receive an acknowledgment within 48 hours.
4. We will triage and respond with a timeline for remediation.

We ask that you give us 90 days to address the issue before any public disclosure.

## Security Measures

### Command Whitelist

`sdlc` enforces a command whitelist for all shell execution. Only pre-approved commands and subcommands are allowed. The default whitelist includes:

- **Read-only**: `ls`, `cat`, `head`, `tail`, `grep`, `find`, `wc`, `sort`, `uniq`
- **Git**: `commit`, `diff`, `log`, `show`, `status`, `add`, `branch`, `checkout`, `pull`, `push`, `fetch`, `merge`, `rebase`
- **Build tools**: `mvn compile/test/package`, `npm install/test/build`, `go build/test/fmt`
- **Container**: `kubectl get/logs/describe/apply`, `docker build/run/ps/logs`

### Dangerous Pattern Blocking

The shell runner rejects commands containing:

- Shell operators: `|`, `;`, `&&`, `||`, `>`, `>>`, `<`
- Command substitution: `$(...)`, backticks
- Path traversal: `..`
- Environment variable access: `$VAR`, `${VAR}`

### No Hardcoded Secrets

- API keys are never stored in code or configuration files
- All credentials are loaded from environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`)
- The rule engine includes a built-in rule (`no-hardcoded-secrets`) that blocks patterns like `password = "..."` or `api_key = "..."` across all source files

### API Key Management

- API keys are referenced by environment variable name in config (`api_key_env: ANTHROPIC_API_KEY`)
- Keys are read at runtime via `os.environ.get()`
- No keys are logged or persisted to disk
- LLM providers fail gracefully with clear error messages when keys are missing

### Audit Trail

All security-relevant events are recorded in JSONL audit logs:

- `rule_violation` — detected rule violations
- `gate_triggered` — quality gate evaluations
- `llm_called` / `llm_fallback` — LLM provider calls and failovers
- `cost_exceeded` — budget threshold breaches
- `file_written` — file system modifications
- `error` — runtime errors

Audit logs are append-only and include timestamps, pipeline IDs, and event details for full traceability.

### Cost Controls

- `CostTracker` enforces a configurable budget limit (`max_cost_usd`)
- Budget breaches emit `COST_EXCEEDED` audit events
- Per-call cost tracking by model