"""Context Climber agent - traces import dependencies via AST parsing."""

import ast
import logging
from collections import deque
from pathlib import Path

from app.state import SynaptixState

logger = logging.getLogger(__name__)


def climb(state: SynaptixState) -> dict[str, dict[str, list[str]]]:
    """Trace import dependencies from entry points and build a dependency DAG."""
    repo_path = Path(state["repo_path"])
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
            repo_path / current,
            repo_path,
            discovered,
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
    logger.info("Traced %d dependency edges across %d files", total_edges, len(edges))
    return {"dependency_edges": edges}


def _extract_local_imports(
    filepath: Path,
    repo_root: Path,
    known_files: set[str],
) -> list[str]:
    try:
        tree = ast.parse(filepath.read_text(), filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return []

    file_dir = filepath.parent
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
    repo_root: Path,
    file_dir: Path,
    known_files: set[str],
    out: list[str],
) -> None:
    """Resolve a module name to a known file path and append it to out."""
    parts = module.split(".")
    candidates = [
        str(Path(*parts)) + ".py",
        str(Path(*parts, "__init__.py")),
    ]

    rel_from_root = file_dir.relative_to(repo_root)
    if str(rel_from_root) != ".":
        candidates += [
            str(rel_from_root / Path(*parts)) + ".py",
            str(rel_from_root / Path(*parts, "__init__.py")),
        ]

    for candidate in candidates:
        normalized = str(Path(candidate))
        if normalized in known_files:
            out.append(normalized)
            return
