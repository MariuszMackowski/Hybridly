from dataclasses import asdict
from pathlib import Path

import typer

import app.models_registry  # noqa: F401
from app.activities.service import reparse_all
from app.db import SessionLocal
from app.exercises.service import upsert_catalog
from app.imports.gravitus.importer import import_gravitus

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


if __name__ == "__main__":
    cli()
