from enum import StrEnum


class AuditEventType(StrEnum):
    PIPELINE_START = "pipeline_start"
    PIPELINE_END = "pipeline_end"
    ENTRY_DETECTED = "entry_detected"
    ADAPTER_DETECTED = "adapter_detected"
    PROFILE_RESOLVED = "profile_resolved"
    PIPELINE_BUILT = "pipeline_built"
    STAGE_START = "stage_start"
    STAGE_END = "stage_end"
    ARTIFACT_CREATED = "artifact_created"
    KB_UPDATED = "kb_updated"
    KB_INIT = "kb_init"
    RULE_VIOLATION = "rule_violation"
    RULE_CHECK = "rule_check"
    GATE_TRIGGERED = "gate_triggered"
    GATE_DECISION = "gate_decision"
    LLM_CALLED = "llm_called"
    LLM_FALLBACK = "llm_fallback"
    LLM_CACHED = "llm_cached"
    SUBAGENT_INVOKED = "subagent_invoked"
    MCP_CALLED = "mcp_called"
    SKILL_USED = "skill_used"
    FILE_WRITTEN = "file_written"
    ERROR = "error"
    RESUME = "resume"
    COST_EXCEEDED = "cost_exceeded"
    SNAPSHOT_TAKEN = "snapshot_taken"
    CONFIG_LOADED = "config_loaded"
    # --- v2.0 pre-seeded event types (added up-front so parallel milestone
    # worktrees never contend on this shared enum). Not all are emitted yet. ---
    # Pillar 1 — agent intelligence
    TOOL_CALLED = "tool_called"          # M-A1: any subagent tool invocation
    SHELL_RUN = "shell_run"              # M-A1: shell tool execution
    REFLECT_STEP = "reflect_step"        # M-A2: Plan-Act-Reflect reflection pass
    CLARIFICATION_REQUESTED = "clarification_requested"  # M-A3
    DELEGATE_SPAWNED = "delegate_spawned"  # M-A5: orchestrator dispatched worker
    # Pillar 2 — collaboration
    PIPELINE_SUSPENDED = "pipeline_suspended"    # M-B1: async gate/clarification
    APPROVAL_GRANTED = "approval_granted"        # M-B1
    APPROVAL_REJECTED = "approval_rejected"      # M-B1
    SLA_ESCALATED = "sla_escalated"              # M-B1
    # Pillar 3 — ecosystem
    PLUGIN_INSTALLED = "plugin_installed"        # M-C2
    # Pillar 4 — eval/quality
    EVAL_SCORED = "eval_scored"          # M-D2: LLM-as-judge score recorded
    FEEDBACK_RECORDED = "feedback_recorded"  # M-D5: outcome → effect score
