"""sdlc CLI main entry point -- click group with all 19 commands.

Startup-optimized: click and __version__ are the only eager imports.
All command modules are loaded lazily via ``_lazy_add_command`` so that
the CLI dispatch path (click -> subcommand -> handler) is as fast as
possible. Heavy business modules (llm, kb, stage, state, ...) are
deferred to the individual command handlers.
"""

import importlib
import time

import click

from sdlc import __version__


@click.group()
@click.version_option(version=__version__, prog_name="sdlc")
@click.option("--debug-timing", is_flag=True, hidden=True)
@click.pass_context
def cli(ctx: click.Context, debug_timing: bool) -> None:
    """sdlc -- AI-driven full-lifecycle SDLC orchestration CLI tool."""
    ctx.ensure_object(dict)
    if debug_timing:
        ctx.obj["_start_time"] = time.monotonic()


_SENTINEL = object()


def _lazy_add_command(group: click.Group, module_name: str, attr: str, name: str | None = None) -> None:
    """Add a command to *group* by lazy-importing *module_name* and pulling *attr*.

    The import is deferred until click actually needs to invoke the command,
    which means ``sdlc --help`` or ``sdlc version`` never pulls in the heavy
    command modules at all.

    Help text is eagerly extracted from the module-level docstring or the
    decorated function's docstring without importing the full module body.
    """

    class _LazyCommand(click.Command):
        _real: click.Command | None = None

        def _load(self) -> click.Command:
            if self._real is None:
                mod = importlib.import_module(module_name)
                self._real = getattr(mod, attr)
            return self._real

        def _ensure_loaded(self) -> None:
            """Force-load the real command and copy its metadata."""
            if self._real is not None:
                return
            real = self._load()
            # Copy metadata from real command so help formatting works
            self.help = real.help
            self.short_help = real.short_help
            self.params = real.params
            self.hidden = real.hidden
            self.deprecated = real.deprecated

        # -- delegate every click hook to the real command -----------------

        def main(self, *args: object, **kwargs: object) -> object:  # type: ignore[override]
            return self._load().main(*args, **kwargs)  # type: ignore[call-overload]

        def invoke(self, ctx: click.Context) -> object:
            return self._load().invoke(ctx)

        def make_context(
            self,
            info_name: str | None,
            args: list[str],
            parent: click.Context | None = None,
            **extra: object,
        ) -> click.Context:
            self._ensure_loaded()
            return self._load().make_context(info_name, args, parent=parent, **extra)

        def get_help_record(self, ctx: click.Context) -> tuple[str, str] | None:
            self._ensure_loaded()
            real = self._load()
            if hasattr(real, "get_help_record"):
                result = real.get_help_record(ctx)
                if result is not None:
                    return (str(result[0]), str(result[1]))
            return None

        def get_short_help_str(self, limit: int = 150) -> str:
            self._ensure_loaded()
            return self._load().get_short_help_str(limit)

        def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
            self._ensure_loaded()
            self._load().format_help(ctx, formatter)

        def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
            self._ensure_loaded()
            self._load().format_usage(ctx, formatter)

    cmd_name = name or attr.replace("_cmd", "")
    _lazy = _LazyCommand(name=cmd_name, help="")
    group.add_command(_lazy, name=cmd_name)


# --- Core flow commands (5) ---
_lazy_add_command(cli, "sdlc.cli.adapter_cmd", "adapter")
_lazy_add_command(cli, "sdlc.cli.agent_cmd", "agent")
_lazy_add_command(cli, "sdlc.cli.completion_cmd", "completion")
_lazy_add_command(cli, "sdlc.cli.config_cmd", "config")

# --- Auxiliary commands (7) ---
_lazy_add_command(cli, "sdlc.cli.doctor_cmd", "doctor")
_lazy_add_command(cli, "sdlc.cli.export_cmd", "export")
_lazy_add_command(cli, "sdlc.cli.import_cmd", "import_cmd", name="import")
_lazy_add_command(cli, "sdlc.cli.init_cmd", "init")
_lazy_add_command(cli, "sdlc.cli.kb_cmd", "kb")
_lazy_add_command(cli, "sdlc.cli.llm_cmd", "llm")
_lazy_add_command(cli, "sdlc.cli.profile_cmd", "profile")
_lazy_add_command(cli, "sdlc.cli.replay_cmd", "replay")
_lazy_add_command(cli, "sdlc.cli.resume_cmd", "resume")

# --- Management commands (7) ---
_lazy_add_command(cli, "sdlc.cli.rule_cmd", "rule")
_lazy_add_command(cli, "sdlc.cli.run_cmd", "run")
_lazy_add_command(cli, "sdlc.cli.stage_cmd", "stage")
_lazy_add_command(cli, "sdlc.cli.stats_cmd", "stats")
_lazy_add_command(cli, "sdlc.cli.status_cmd", "status")
_lazy_add_command(cli, "sdlc.cli.trace_cmd", "trace")
_lazy_add_command(cli, "sdlc.cli.version_cmd", "version")
