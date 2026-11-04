import typer

import app.models_registry  # noqa: F401
from app.db import SessionLocal
from app.exercises.service import upsert_catalog

cli = typer.Typer(no_args_is_help=True)


@cli.command("seed-exercises")
def seed_exercises() -> None:
    """Insert the starting exercise catalog (skips existing names)."""
    with SessionLocal() as db:
        typer.echo(f"exercises added: {upsert_catalog(db)}")


if __name__ == "__main__":
    cli()
