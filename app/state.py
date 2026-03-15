"""Shared state schema for the Synaptix pipeline."""

from typing import NotRequired, TypedDict


class SynaptixState(TypedDict):
    """State schema for the Synaptix agent pipeline."""

    repo_path: str
    discovered_files: list[str]
    entry_points: list[str]
    dependency_edges: dict[str, list[str]]
    file_labels: NotRequired[dict[str, str]]
    mermaid_output: NotRequired[str]
    output_file: NotRequired[str]
