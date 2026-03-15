import os

import chromadb


def index(state: dict) -> dict:
    repo_path: str = state["repo_path"]
    discovered: list[str] = state["discovered_files"]
    entry_points: set[str] = set(state["entry_points"])

    db_path = os.path.join(repo_path, ".synaptix_db")
    client = chromadb.PersistentClient(path=db_path)

    try:
        client.delete_collection("codebase")
    except Exception:
        pass
    collection = client.create_collection("codebase")

    docs: list[str] = []
    ids: list[str] = []
    metas: list[dict[str, str | bool]] = []

    for rel in discovered:
        try:
            with open(os.path.join(repo_path, rel), "r") as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        if not content.strip():
            continue
        docs.append(content[:8000])
        ids.append(rel)
        metas.append({"path": rel, "is_entry": rel in entry_points})

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metas)

    print(f"  Indexed {len(docs)} files into ChromaDB")
    return {}
