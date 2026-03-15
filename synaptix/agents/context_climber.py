import ast
import os
from collections import deque


def climb(state: dict) -> dict[str, dict[str, list[str]]]:
    repo_path: str = state["repo_path"]
    discovered: set[str] = set(state["discovered_files"])
    entry_points: list[str] = state["entry_points"]

    edges: dict[str, list[str]] = {}
    visited: set[str] = set()
    queue: deque[str] = deque(entry_points)

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        imports = _extract_local_imports(
            os.path.join(repo_path, current), repo_path, discovered
        )
        if imports:
            edges[current] = imports
        for imp in imports:
            if imp not in visited:
                queue.append(imp)

    for rel in discovered:
        if rel not in visited and rel not in edges:
            edges.setdefault(rel, [])

    total_edges = sum(len(v) for v in edges.values())
    print(f"  Traced {total_edges} dependency edges across {len(edges)} files")
    return {"dependency_edges": edges}


def _extract_local_imports(
    filepath: str, repo_root: str, known_files: set[str]
) -> list[str]:
    try:
        with open(filepath, "r") as f:
            tree = ast.parse(f.read(), filename=filepath)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return []

    file_dir = os.path.dirname(filepath)
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            _resolve_and_add(node.module, repo_root, file_dir, known_files, imports)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                _resolve_and_add(alias.name, repo_root, file_dir, known_files, imports)

    return sorted(set(imports))


def _resolve_and_add(
    module: str,
    repo_root: str,
    file_dir: str,
    known_files: set[str],
    out: list[str],
) -> None:
    parts = module.split(".")
    candidates = [
        os.path.join(*parts) + ".py",
        os.path.join(*parts, "__init__.py"),
    ]

    rel_from_root = os.path.relpath(file_dir, repo_root)
    if rel_from_root != ".":
        candidates += [
            os.path.join(rel_from_root, *parts) + ".py",
            os.path.join(rel_from_root, *parts, "__init__.py"),
        ]

    for candidate in candidates:
        normalized = os.path.normpath(candidate)
        if normalized in known_files:
            out.append(normalized)
            return
