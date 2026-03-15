"""Semantic Indexer agent - vectorizes code chunks into ChromaDB."""

import contextlib
import logging
from pathlib import Path

import chromadb

from app.state import SynaptixState

logger = logging.getLogger(__name__)


def index(state: SynaptixState) -> dict[str, str]:
    """Index discovered files into a ChromaDB vector collection."""
    repo_path = Path(state["repo_path"])
    discovered: list[str] = state["discovered_files"]
    entry_points: set[str] = set(state["entry_points"])

    db_path = repo_path / ".synaptix_db"
    client = chromadb.PersistentClient(path=str(db_path))

    with contextlib.suppress(ValueError):
        client.delete_collection("codebase")
    collection = client.create_collection("codebase")

    docs: list[str] = []
    ids: list[str] = []
    metas: list[dict[str, str | bool]] = []

    for rel in discovered:
        try:
            content = (repo_path / rel).read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        if not content.strip():
            continue
        docs.append(content[:8000])
        ids.append(rel)
        metas.append({"path": rel, "is_entry": rel in entry_points})

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metas)

    logger.info("Indexed %d files into ChromaDB", len(docs))
    return {}
