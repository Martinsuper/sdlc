# Security Policy

## Reporting a Vulnerability

If you discover a security issue in the `sdlc` skill, please report it responsibly:

1. **Do not** file a public issue.
2. Email the maintainers at **security@sdlc.dev** with:
   - Description of the issue
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. You will receive an acknowledgment within 48 hours.
4. We will triage and respond with a timeline for remediation.

We ask that you give us 90 days to address the issue before any public disclosure.

## Scope

`sdlc` is a **prompt-only Agent Skill for OpenCode and Claude Code** — it ships no runtime, no
network service, and no credential handling of its own. It consists of
Markdown prompts, commands, templates, and checklists at the repository root
(`SKILL.md`, `commands/`, `references/`, `templates/`). Any
execution (file edits, shell commands, LLM calls) happens through the active
coding client, governed by that client's permission model and sandbox.

Security-relevant concerns for this repository are therefore limited to
the **content** of the prompts, for example:

- **No hardcoded secrets** — prompts and templates must never contain API
  keys, tokens, internal hostnames, or other credentials. Report any that
  slip in.
- **No prompt injection sinks** — prompt text that instructs the agent to
  exfiltrate data, disable safety checks, or run destructive commands
  unprompted.
- **No unsafe command guidance** — templates/checklists should not tell
  users to run destructive or credential-leaking commands.

Vulnerabilities in OpenCode or Claude Code (the harness that executes this skill)
should be reported to the corresponding client project, not here.
