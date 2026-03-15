"""Mermaid Renderer - converts labeled DAG to Mermaid.js flowchart."""

import re
from pathlib import Path

from app.state import SynaptixState


def render(state: SynaptixState) -> dict[str, str]:
    """Render the dependency graph as a Mermaid flowchart and save to file."""
    repo_path = Path(state["repo_path"])
    edges: dict[str, list[str]] = state["dependency_edges"]
    labels: dict[str, str] = state.get("file_labels", {})

    all_files: set[str] = set(edges.keys()) | {
        f for deps in edges.values() for f in deps
    }
    node_ids: dict[str, str] = {f: f"n{i}" for i, f in enumerate(sorted(all_files))}

    lines: list[str] = ["flowchart TD"]

    for f in sorted(all_files):
        nid = node_ids[f]
        label = labels.get(f, f)
        safe_label = _sanitize(f"{f}\\n{label}")
        lines.append(f'    {nid}["{safe_label}"]')

    for src, deps in sorted(edges.items()):
        lines.extend(
            f"    {node_ids[src]} --> {node_ids[dep]}"
            for dep in sorted(deps)
            if src in node_ids and dep in node_ids
        )

    mermaid = "\n".join(lines)

    out_path = repo_path / "synaptix_output.md"
    out_path.write_text(
        f"# Synaptix - Repository Mental Map\n\n```mermaid\n{mermaid}\n```\n",
    )

    return {"mermaid_output": mermaid, "output_file": str(out_path)}


def _sanitize(text: str) -> str:
    return re.sub(r'["\[\]{}()<>]', "", text)
