import os
import re


def render(state: dict) -> dict[str, str]:
    repo_path: str = state["repo_path"]
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
        for dep in sorted(deps):
            if src in node_ids and dep in node_ids:
                lines.append(f"    {node_ids[src]} --> {node_ids[dep]}")

    mermaid = "\n".join(lines)

    out_path = os.path.join(repo_path, "synaptix_output.md")
    with open(out_path, "w") as f:
        f.write(f"# Synaptix - Repository Mental Map\n\n```mermaid\n{mermaid}\n```\n")

    return {"mermaid_output": mermaid, "output_file": out_path}


def _sanitize(text: str) -> str:
    return re.sub(r'["\[\]{}()<>]', "", text)
