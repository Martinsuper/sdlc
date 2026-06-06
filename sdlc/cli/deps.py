"""sdlc.cli.deps -- DependencyContainer: assembles all engines."""

from __future__ import annotations

from dataclasses import dataclass

from sdlc.adapter import AdapterRegistry, register_dongboot
from sdlc.audit import AuditLogger
from sdlc.core import EntryDetector, PipelineBuilder, RunCoordinator
from sdlc.gate import GateEngine
from sdlc.kb.memory import MemoryL2
from sdlc.llm import CostTracker, MultiLLMClient
from sdlc.profile import ProfileRegistry
from sdlc.profile import register_builtins as register_profiles
from sdlc.stage import StageCatalog
from sdlc.state import StateStore
from sdlc.subagent import SubagentPool, SubagentRegistry
from sdlc.subagent import register_builtins as register_subagents
from sdlc.utils.config import SdlcConfig
from sdlc.utils.config_loader import load_config
from sdlc.utils.paths import project_root, sdlc_home


@dataclass
class DependencyContainer:
    config: SdlcConfig
    state: StateStore
    audit: AuditLogger
    catalog: StageCatalog
    profiles: ProfileRegistry
    adapters: AdapterRegistry
    gates: GateEngine
    subagent_pool: SubagentPool
    entry_detector: EntryDetector
    pipeline_builder: PipelineBuilder
    coordinator: RunCoordinator
    cost_tracker: CostTracker


def _register_all_adapters(registry: AdapterRegistry) -> None:
    """Register all builtin adapters into the given registry."""
    from sdlc.adapter import (
        register_data_spark,
        register_frontend_react,
        register_frontend_vue,
        register_go_gin,
        register_go_kratos,
        register_infra_terraform,
        register_jd_spring_boot,
        register_mobile_android,
        register_mobile_flutter,
        register_mobile_ios,
        register_no_tech,
        register_node_express,
        register_node_nestjs,
        register_python_django,
        register_python_fastapi,
        register_python_flask,
        register_rust_axum,
    )

    register_data_spark(registry)
    register_dongboot(registry)
    register_frontend_react(registry)
    register_frontend_vue(registry)
    register_go_gin(registry)
    register_go_kratos(registry)
    register_infra_terraform(registry)
    register_jd_spring_boot(registry)
    register_mobile_android(registry)
    register_mobile_flutter(registry)
    register_mobile_ios(registry)
    register_node_express(registry)
    register_node_nestjs(registry)
    register_no_tech(registry)
    register_python_django(registry)
    register_python_fastapi(registry)
    register_python_flask(registry)
    register_rust_axum(registry)


def build_deps(config: SdlcConfig | None = None) -> DependencyContainer:
    """Assemble all dependencies as singletons."""
    if config is None:
        config = load_config()

    home = sdlc_home()
    home.mkdir(exist_ok=True)

    state = StateStore(home / "state.db")
    audit = AuditLogger(home / "audit.jsonl")
    catalog = StageCatalog()
    catalog.load_builtin()

    profiles = ProfileRegistry()
    register_profiles(profiles)

    adapters = AdapterRegistry()
    _register_all_adapters(adapters)

    gates = GateEngine(audit)

    sub_registry = SubagentRegistry()
    register_subagents(sub_registry)

    # Build LLM providers via factory
    from sdlc.llm.client import ModelRouter
    from sdlc.llm.provider_factory import ProviderFactory

    primary = ProviderFactory.create(config.llm)
    fallback = ProviderFactory.create_fallback(config.llm)

    router = ModelRouter(
        provider_type=config.llm.provider,
        default_model=config.llm.model,
    )
    llm = MultiLLMClient(primary=primary, fallback=fallback, router=router)
    subagent_pool = SubagentPool(registry=sub_registry, llm=llm, audit=audit)

    max_cost = (
        config.llm.max_cost_usd
        if hasattr(config, "llm") and hasattr(config.llm, "max_cost_usd")
        else 5.0
    )
    cost_tracker = CostTracker(max_budget_usd=max_cost)

    # Memory L2: auto-update KB after stages
    memory_l2: MemoryL2 | None = None
    try:
        kb_root = project_root() / "doc" / "kb"
        if kb_root.exists():
            memory_l2 = MemoryL2(kb_root=kb_root)
    except Exception:
        memory_l2 = None

    coordinator = RunCoordinator(
        state=state,
        audit=audit,
        catalog=catalog,
        subagent_pool=subagent_pool,
        gate_engine=gates,
        profile_registry=profiles,
        adapter_registry=adapters,
        cost_tracker=cost_tracker,
        memory_l2=memory_l2,
    )

    return DependencyContainer(
        config=config,
        state=state,
        audit=audit,
        catalog=catalog,
        profiles=profiles,
        adapters=adapters,
        gates=gates,
        subagent_pool=subagent_pool,
        entry_detector=EntryDetector(),
        pipeline_builder=PipelineBuilder(catalog),
        coordinator=coordinator,
        cost_tracker=cost_tracker,
    )
