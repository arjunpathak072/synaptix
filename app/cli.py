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
def main(path: str) -> None:
    """Synaptix - Build a Mental Map of any Python repository."""
    repo_path = str(Path(path).resolve())
    click.echo(f"Scanning: {repo_path}\n")

    graph = build_graph()
    result = graph.invoke({"repo_path": repo_path})

    if result.get("mermaid_output"):
        click.echo("\nDependency Graph (Mermaid):\n")
        click.echo(result["mermaid_output"])

    if result.get("output_file"):
        click.echo(f"\nSaved to: {result['output_file']}")
