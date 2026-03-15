"""CLI interface for Synaptix."""

from pathlib import Path

import click

from app.graph import build_graph


@click.command()
@click.option(
    "--path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Path to the Python repository to analyze",
)
@click.option(
    "--chat",
    is_flag=True,
    default=False,
    help="Launch interactive TUI to ask questions about the codebase",
)
def main(path: str, chat: bool) -> None:
    """Synaptix - Build a Mental Map of any Python repository."""
    repo_path = str(Path(path).resolve())

    db_path = Path(repo_path) / ".synaptix_db"
    has_index = False
    if db_path.exists():
        import chromadb

        try:
            c = chromadb.PersistentClient(path=str(db_path))
            c.get_collection("codebase")
            has_index = True
        except Exception:
            pass

    run_pipeline = not chat or not has_index

    if run_pipeline:
        click.echo(f"Scanning: {repo_path}\n")
        graph = build_graph()
        result = graph.invoke({"repo_path": repo_path})

        if result.get("mermaid_output"):
            click.echo("\nDependency Graph (Mermaid):\n")
            click.echo(result["mermaid_output"])
        if result.get("output_file"):
            click.echo(f"\nSaved to: {result['output_file']}")

    if chat:
        from app.tui import run_tui

        run_tui(repo_path)
