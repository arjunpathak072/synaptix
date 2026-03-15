import os
import re

from langchain_ollama import ChatOllama

PROMPT = (
    "You are a code analyst. Given this Python file, respond with ONLY a short label "
    "(max 6 words) describing its role, e.g. 'API route handler' or 'Database utilities'. "
    "No explanation, no thinking, just the label.\n\nFile: {path}\n\n```python\n{code}\n```"
)


def resolve(state: dict) -> dict[str, dict[str, str]]:
    repo_path: str = state["repo_path"]
    edges: dict[str, list[str]] = state["dependency_edges"]
    all_files: set[str] = set(edges.keys()) | {
        f for deps in edges.values() for f in deps
    }

    labels: dict[str, str] = {}
    llm: ChatOllama | None = None

    try:
        llm = ChatOllama(model="qwen3", temperature=0)
        llm.invoke("test")
    except Exception as e:
        print(f"  Ollama unavailable ({e}), using filename labels")
        llm = None

    for rel in sorted(all_files):
        if llm:
            try:
                with open(os.path.join(repo_path, rel), "r") as f:
                    code = f.read()[:4000]
                resp = llm.invoke(PROMPT.format(path=rel, code=code))
                assert isinstance(resp.content, str)
                label = _clean_label(resp.content)
                labels[rel] = label or _fallback_label(rel)
                continue
            except Exception:
                pass
        labels[rel] = _fallback_label(rel)

    source = "Ollama/qwen3" if llm else "filename fallback"
    print(f"  Labeled {len(labels)} files via {source}")
    return {"file_labels": labels}


def _clean_label(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text.strip("\"'").strip()


def _fallback_label(rel: str) -> str:
    base = os.path.basename(rel)
    if base == "__init__.py":
        return "Package init"
    if base == "__main__.py":
        return "CLI entry point"
    return os.path.splitext(base)[0].replace("_", " ").title()
