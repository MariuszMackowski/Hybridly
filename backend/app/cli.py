from dataclasses import asdict
from pathlib import Path

import typer

import app.models_registry  # noqa: F401
from app.activities.service import reparse_all
from app.db import SessionLocal
from app.exercises.service import upsert_catalog
from app.imports.gravitus.importer import import_gravitus
from app.plans.service import import_plan
from app.time import local_today

cli = typer.Typer(no_args_is_help=True)


@cli.command("seed-exercises")
def seed_exercises() -> None:
    """Insert the starting exercise catalog (skips existing names)."""
    with SessionLocal() as db:
        typer.echo(f"exercises added: {upsert_catalog(db)}")


@cli.command("import-gravitus")
def import_gravitus_cmd(path: Path) -> None:
    """Import a Gravitus CSV export (safe to re-run)."""
    with SessionLocal() as db:
        report = import_gravitus(db, path.read_text(encoding="utf-8"))
    for key, value in asdict(report).items():
        typer.echo(f"{key}: {value}")


@cli.command("reparse-activities")
def reparse_activities() -> None:
    """Re-read stored FIT files to fill fields added to the parser."""
    with SessionLocal() as db:
        typer.echo(f"activities reparsed: {reparse_all(db)}")


@cli.command("import-plan")
def import_plan_cmd(path: Path) -> None:
    """Import a running plan YAML (takes over from max(first week, today))."""
    with SessionLocal() as db:
        plan = import_plan(db, path.read_text(encoding="utf-8"), local_today())
        sessions = sum(len(w.sessions) for w in plan.weeks)
        typer.echo(
            f"plan {plan.name!r}: {len(plan.weeks)} weeks, {sessions} sessions, "
            f"effective from {plan.effective_from}"
        )


if __name__ == "__main__":
    cli()
