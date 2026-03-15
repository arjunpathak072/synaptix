import ast
import os

EXCLUDE_DIRS: set[str] = {
    "venv",
    ".venv",
    "__pycache__",
    ".git",
    "node_modules",
    ".tox",
    ".eggs",
    "dist",
    "build",
}
ENTRY_FILENAMES: set[str] = {"main.py", "__main__.py", "app.py", "manage.py"}


def discover(state: dict) -> dict[str, list[str]]:
    repo_path: str = state["repo_path"]
    discovered: list[str] = []
    entry_points: list[str] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in files:
            if not name.endswith(".py"):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, repo_path)
            discovered.append(rel)

            if name in ENTRY_FILENAMES or _has_main_guard(full):
                entry_points.append(rel)

    print(f"  Discovered {len(discovered)} Python files")
    print(f"  Entry points: {entry_points or ['(none found, scanning all files)']}")

    if not entry_points:
        entry_points = list(discovered)

    return {"discovered_files": discovered, "entry_points": entry_points}


def _has_main_guard(filepath: str) -> bool:
    try:
        with open(filepath, "r") as f:
            tree = ast.parse(f.read(), filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        ):
            return True
    return False
