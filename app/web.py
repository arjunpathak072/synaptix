"""Flask-based Code Wiki: split-screen Mermaid diagram + chat."""

import json
from pathlib import Path

import chromadb
import ollama
from flask import Flask, Response, render_template, request, stream_with_context

from app.prompts import load

app = Flask(__name__)

_repo_path: str = ""
_collection: "chromadb.Collection | None" = None
_messages: list[dict[str, str]] = []


def init(repo_path: str) -> None:
    global _repo_path, _collection, _messages
    _repo_path = repo_path

    db_path = Path(repo_path) / ".synaptix_db"
    if db_path.exists():
        client = chromadb.PersistentClient(path=str(db_path))
        try:
            _collection = client.get_collection("codebase")
        except Exception:
            _collection = None

    _messages = [{"role": "system", "content": _build_system_prompt()}]


def _build_system_prompt() -> str:
    parts = [load("system").format(repo_path=_repo_path)]

    output_md = Path(_repo_path) / "synaptix_output.md"
    if output_md.exists():
        parts += ["", "PROJECT DEPENDENCY GRAPH AND MODULE ROLES:", output_md.read_text()]

    if _collection and _collection.count() > 0:
        all_data = _collection.get(include=["metadatas"])
        files, entries = [], []
        for meta in all_data["metadatas"]:
            path = meta.get("path", "")
            files.append(path)
            if meta.get("is_entry"):
                entries.append(path)
        parts += ["", f"ALL PROJECT FILES ({len(files)}):", *[f"  - {f}" for f in sorted(files)]]
        if entries:
            parts += ["", "ENTRY POINTS:", *[f"  - {e}" for e in sorted(entries)]]

    parts += ["", "Use the retrieved source code snippets to give precise answers."]
    return "\n".join(parts)


def _retrieve_context(question: str, n_results: int = 6) -> tuple[str, str]:
    if not _collection or _collection.count() == 0:
        return "", ""

    results = _collection.query(
        query_texts=[question], n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    chunks, trace_lines, seen = [], [], set()

    RELEVANCE_THRESHOLD = 1.75

    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0], strict=False,
    ):
        if dist > RELEVANCE_THRESHOLD:
            continue

        path = meta.get("path", "unknown")
        sym = meta.get("symbol_name", "")
        kind = meta.get("symbol_kind", "file")
        start, end = meta.get("start_line", 0), meta.get("end_line", 0)

        key = f"{path}::{sym}" if sym else path
        if key in seen:
            continue
        seen.add(key)

        full_path = Path(_repo_path) / path
        try:
            lines = full_path.read_text().splitlines()
            source = "\n".join(lines[start : end + 1])
        except (FileNotFoundError, UnicodeDecodeError):
            source = doc[:3000]

        header = f"--- {path}"
        if sym:
            header += f" | {kind} `{sym}` (L{start + 1}-{end + 1})"
        chunks.append(f"{header} ---\n{source}")

        loc = f"`{path}` → {kind} **{sym}** (L{start + 1}–{end + 1})" if sym else f"`{path}`"
        trace_lines.append(f"- {loc}  · distance: `{dist:.4f}`")

    return "\n\n".join(chunks), "\n".join(trace_lines)


def _load_mermaid() -> str:
    output_md = Path(_repo_path) / "synaptix_output.md"
    if not output_md.exists():
        return "graph TD\n    A[No diagram yet — run the pipeline first]"
    text = output_md.read_text()
    start = text.find("```mermaid")
    end = text.find("```", start + 10)
    if start == -1:
        return "graph TD\n    A[Could not parse diagram]"
    return text[start + 10 : end].strip()


@app.route("/")
def index():
    return render_template("index.html", repo_path=_repo_path, mermaid_code=_load_mermaid())


@app.route("/chat", methods=["POST"])
def chat():
    question = request.json.get("message", "").strip()
    if not question:
        return Response("data: " + json.dumps({"type": "error", "content": "Empty message"}) + "\n\n",
                        content_type="text/event-stream")

    def generate():
        context, trace = _retrieve_context(question)

        if trace:
            yield f"data: {json.dumps({'type': 'trace', 'content': trace})}\n\n"

        user_content = f"Relevant source code:\n\n{context}\n\nQuestion: {question}" if context else question
        _messages.append({"role": "user", "content": user_content})

        full_response = ""
        try:
            for chunk in ollama.chat(model="qwen3", messages=_messages, stream=True):
                token = chunk["message"]["content"]
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        _messages.append({"role": "assistant", "content": full_response})

    return Response(stream_with_context(generate()), content_type="text/event-stream")


def run_web(repo_path: str, port: int = 5000) -> None:
    init(repo_path)
    print(f"\n🧠 Synaptix Explorer: http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
