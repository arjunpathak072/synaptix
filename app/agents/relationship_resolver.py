"""Relationship Resolver agent - uses LLM to semantically label each module."""

import logging
import re
from pathlib import Path

from langchain_ollama import ChatOllama

from app.prompts import load
from app.state import SynaptixState

logger = logging.getLogger(__name__)


def resolve(state: SynaptixState) -> dict[str, dict[str, str]]:
    """Label each module's role using LLM or filename fallback."""
    repo_path = Path(state["repo_path"])
    edges: dict[str, list[str]] = state["dependency_edges"]
    all_files: set[str] = set(edges.keys()) | {
        f for deps in edges.values() for f in deps
    }

    labels: dict[str, str] = {}
    llm: ChatOllama | None = None

    try:
        llm = ChatOllama(model="qwen3", temperature=0)
        llm.invoke("test")
    except (ConnectionError, RuntimeError, OSError) as e:
        logger.warning("Ollama unavailable (%s), using filename labels", e)
        llm = None

    for rel in sorted(all_files):
        if llm:
            try:
                code = (repo_path / rel).read_text()[:4000]
                resp = llm.invoke(load("label").format(path=rel, code=code))
                if isinstance(resp.content, str):
                    label = _clean_label(resp.content)
                    labels[rel] = label or _fallback_label(rel)
                    continue
            except (OSError, RuntimeError):
                logger.debug("LLM failed for %s, using fallback", rel)
        labels[rel] = _fallback_label(rel)

    source = "Ollama/qwen3" if llm else "filename fallback"
    logger.info("Labeled %d files via %s", len(labels), source)
    return {"file_labels": labels}


def _clean_label(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text.strip("\"'").strip()


def _fallback_label(rel: str) -> str:
    path = Path(rel)
    if path.name == "__init__.py":
        return "Package init"
    if path.name == "__main__.py":
        return "CLI entry point"
    return path.stem.replace("_", " ").title()
