"""Command line helpers for the WebWatcher backend."""

from __future__ import annotations

import asyncio

import typer

from .database import init_db
from .services import EmailNotifier, IngestionService, run_ingestion

cli = typer.Typer(help="WebWatcher backend utilities")


@cli.command()
def initdb() -> None:
    """Initialise the SQLite database."""

    async def _run() -> None:
        await init_db()

    asyncio.run(_run())
    typer.echo("Database initialised ✅")


@cli.command()
def ingest() -> None:
    """Run the ingestion pipeline and send Telegram alerts."""

    async def _run() -> None:
        ingested, notified = await run_ingestion()
        typer.echo(f"Ingested {ingested} entries, notified {notified} channels")

    asyncio.run(_run())


@cli.command()
def digest() -> None:
    """Send an email digest with the latest entries."""

    async def _run() -> None:
        ingestion = IngestionService()
        email = EmailNotifier()
        try:
            _, items = await ingestion.ingest_all()
            sent = await email.send_digest(items)
            typer.echo("Digest sent" if sent else "Digest not sent (missing configuration or error)")
        finally:
            await ingestion.close()
            await email.close()

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
