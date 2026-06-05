"""sdlc CLI main entry point — click group with all 19 commands."""

import click

from sdlc import __version__


@click.group()
@click.version_option(version=__version__, prog_name="sdlc")
def cli() -> None:
    """sdlc — AI-driven full-lifecycle SDLC orchestration CLI tool."""


# --- Core flow commands (5) ---
from sdlc.cli.adapter_cmd import adapter  # noqa: E402
from sdlc.cli.agent_cmd import agent  # noqa: E402
from sdlc.cli.completion_cmd import completion  # noqa: E402
from sdlc.cli.config_cmd import config  # noqa: E402

# --- Auxiliary commands (7) ---
from sdlc.cli.doctor_cmd import doctor  # noqa: E402
from sdlc.cli.export_cmd import export  # noqa: E402
from sdlc.cli.import_cmd import import_cmd  # noqa: E402
from sdlc.cli.init_cmd import init  # noqa: E402
from sdlc.cli.kb_cmd import kb  # noqa: E402
from sdlc.cli.profile_cmd import profile  # noqa: E402
from sdlc.cli.replay_cmd import replay  # noqa: E402
from sdlc.cli.resume_cmd import resume  # noqa: E402

# --- Management commands (7) ---
from sdlc.cli.rule_cmd import rule  # noqa: E402
from sdlc.cli.run_cmd import run  # noqa: E402
from sdlc.cli.stage_cmd import stage  # noqa: E402
from sdlc.cli.stats_cmd import stats  # noqa: E402
from sdlc.cli.status_cmd import status  # noqa: E402
from sdlc.cli.trace_cmd import trace  # noqa: E402
from sdlc.cli.version_cmd import version  # noqa: E402

# --- Register all commands ---
cli.add_command(run)
cli.add_command(init)
cli.add_command(status)
cli.add_command(resume)
cli.add_command(trace)
cli.add_command(rule)
cli.add_command(kb)
cli.add_command(stage)
cli.add_command(adapter)
cli.add_command(profile)
cli.add_command(agent)
cli.add_command(config)
cli.add_command(doctor)
cli.add_command(version)
cli.add_command(completion)
cli.add_command(replay)
cli.add_command(export)
cli.add_command(import_cmd, name="import")
cli.add_command(stats)
