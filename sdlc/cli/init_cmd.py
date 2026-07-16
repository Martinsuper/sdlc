import click

# NOTE: If init_cmd needs to build an LLM client, use
# sdlc.cli.deps.build_llm_client(config) instead of duplicating the
# provider/router assembly logic here.


@click.command()
@click.argument("path", default=".")
@click.option("--depth", type=int, default=5)
@click.option("--no-llm", is_flag=True)
@click.option("--force", is_flag=True)
@click.option("--template", type=click.Choice(["default", "empty", "full"]), default="default")
@click.option("--adapter", help="Force adapter")
@click.option("--no-commit", is_flag=True)
@click.option("-i", "--interactive", is_flag=True)
def init(path, depth, no_llm, force, template, adapter, no_commit, interactive):
    """Initialize project for sdlc."""
    from pathlib import Path

    from sdlc.adapter.detector import AdapterDetector
    from sdlc.adapter.dongboot import register_dongboot
    from sdlc.adapter.registry import AdapterRegistry
    from sdlc.core.init_detector import InitDetector
    from sdlc.utils.paths import ensure_dir

    project = Path(path).resolve()
    click.echo(f"Initializing sdlc for: {project}")

    # Auto-detect project info
    detector = InitDetector()
    project_info = detector.detect(project)
    click.echo(f"  Detected language: {project_info.language or 'unknown'}")
    if project_info.framework:
        click.echo(f"  Detected framework: {project_info.framework}")
    if project_info.build_tool:
        click.echo(f"  Detected build tool: {project_info.build_tool}")
    if project_info.has_docker:
        click.echo("  Docker detected")
    if project_info.has_ci:
        click.echo("  CI/CD detected")

    # Create .sdlc directory
    sdlc_dir = project / ".sdlc"
    if sdlc_dir.exists() and not force:
        click.echo("  .sdlc/ already exists. Use --force to overwrite.")
        raise SystemExit(1)
    ensure_dir(sdlc_dir)
    click.echo("  Created .sdlc/")

    # Create doc/kb directory structure
    kb_dir = project / "doc" / "kb"
    for subdir in [
        "rules",
        "rules/custom",
        "rules/exceptions",
        "standards",
        "architecture",
        "architecture/adr",
        "memory",
    ]:
        ensure_dir(kb_dir / subdir)
    click.echo("  Created doc/kb/ structure")

    # Create default KB files
    default_files = {
        "conventions.md": "# Conventions\n\nProject conventions (human-maintained).\n",
        "glossary.md": "# Glossary\n\n| Term | Definition | Source |\n|------|-----------|--------|\n",
        "tech-stack.md": "# Tech Stack\n\n| Technology | Version | Purpose | Owner |\n|-----------|---------|---------|-------|\n",
        "lessons-learned.md": (
            "# Lessons Learned\n\n"
            "| Date | Issue | Root Cause | Fix | Lesson |\n|------|-------|-----------|-----|--------|\n"
        ),
        "patterns.md": (
            "# Patterns\n\n"
            "## Pattern Name\n**Context:** ...\n**Solution:** ...\n**Example:** ...\n"
        ),
        "antipatterns.md": (
            "# Anti-patterns\n\n"
            "## Anti-pattern Name\n**Symptoms:** ...\n**Consequences:** ...\n**Better approach:** ...\n"
        ),
    }
    for name, content in default_files.items():
        target = kb_dir / name
        if not target.exists() or force:
            target.write_text(content)
    click.echo("  Created default KB files")

    # Create empty rules files
    for rules_file in ["MUST.yaml", "SHOULD.yaml", "MAY.yaml"]:
        target = kb_dir / "rules" / rules_file
        if not target.exists() or force:
            target.write_text("# Rules file\n[]\n")
    click.echo("  Created rules skeleton")

    # Detect adapters
    if not adapter:
        registry = AdapterRegistry()
        register_dongboot(registry)
        adapter_detector = AdapterDetector(registry)
        detected = adapter_detector.detect(project)
        if detected:
            click.echo("\n  Detected adapters:")
            for a in detected:
                click.echo(f"    {a.id} -- {a.name}")
        else:
            click.echo("\n  No adapters detected (generic project)")
    else:
        click.echo(f"\n  Using adapter: {adapter}")

    # Create .sdlc/ext/config.yaml with auto-detected info.
    # This is the exact path load_config() reads (project layer); the previous
    # .sdlc/config.toml was never read by anything.
    from sdlc.utils.yaml_io import save_yaml

    config_path = sdlc_dir / "ext" / "config.yaml"
    if not config_path.exists() or force:
        config_data = detector.generate_config(project_info, project)
        # Override adapter if explicitly specified via --adapter flag
        if adapter:
            config_data["adapter"] = adapter
        # Shape it so SdlcConfig can consume it: profile must be a mapping
        # ({default, auto_detect}); project/adapter/stages/gates are extra
        # metadata keys (ignored by the model but kept for humans/tooling).
        profile_id = config_data.get("profile", "new-feature")
        config_data["profile"] = {"default": profile_id, "auto_detect": True}
        ensure_dir(config_path.parent)
        save_yaml(config_path, config_data)
        click.echo(f"  Created {config_path.relative_to(project)}")
    click.echo("\n  Project initialized successfully!")
    if not no_commit:
        click.echo('  Tip: Run \'git add .sdlc doc/kb && git commit -m "init: sdlc"\'')
