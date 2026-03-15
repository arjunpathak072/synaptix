"""Interactive TUI for asking questions about the analyzed repository."""

from pathlib import Path

import chromadb
import ollama
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown


from app.prompts import load


def _build_system_prompt(
    repo_path: str, collection: "chromadb.Collection | None"
) -> str:
    """Build a system prompt grounded in the actual project structure."""
    parts = [load("system").format(repo_path=repo_path)]

    # Load the Mermaid output if available — it has the full dependency graph + labels
    output_md = Path(repo_path) / "synaptix_output.md"
    if output_md.exists():
        parts += [
            "",
            "PROJECT DEPENDENCY GRAPH AND MODULE ROLES:",
            output_md.read_text(),
        ]

    # Load file inventory from ChromaDB metadata
    if collection and collection.count() > 0:
        all_data = collection.get(include=["metadatas"])
        files = []
        entries = []
        for meta in all_data["metadatas"]:
            path = meta.get("path", "")
            files.append(path)
            if meta.get("is_entry"):
                entries.append(path)

        parts += [
            "",
            f"ALL PROJECT FILES ({len(files)}):",
            *[f"  - {f}" for f in sorted(files)],
        ]
        if entries:
            parts += [
                "",
                "ENTRY POINTS (where execution starts):",
                *[f"  - {e}" for e in sorted(entries)],
            ]

    parts += [
        "",
        "When the user asks a question, you will also receive relevant source code ",
        "snippets retrieved from the codebase. Use them to give precise answers.",
    ]

    return "\n".join(parts)


class ChatMessage(Markdown):
    """A single chat message displayed as Markdown."""


class SynaptixChat(App):
    """TUI chat interface for querying the analyzed codebase."""

    THEME = "textual-light"

    CSS = """
    Screen {
        background: #ffffff;
    }
    #chat-view {
        overflow-y: auto;
        padding: 1 2;
        background: #ffffff;
    }
    .user-msg {
        background: #e8f0fe;
        color: #1a1a1a;
        margin: 1 0;
        padding: 1 2;
    }
    .assistant-msg {
        background: #f5f5f5;
        color: #1a1a1a;
        margin: 1 0;
        padding: 1 2;
    }
    .trace-msg {
        background: #fff8e1;
        color: #6d4c00;
        margin: 0 0;
        padding: 1 2;
    }
    #prompt-input {
        dock: bottom;
        margin: 0 2 1 2;
    }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self, repo_path: str) -> None:
        super().__init__()
        self.repo_path = repo_path
        self.collection: chromadb.Collection | None = None
        self.messages: list[dict[str, str]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield VerticalScroll(id="chat-view")
        yield Input(placeholder="Ask about the codebase…", id="prompt-input")
        yield Footer()

    def on_mount(self) -> None:
        db_path = Path(self.repo_path) / ".synaptix_db"
        if db_path.exists():
            client = chromadb.PersistentClient(path=str(db_path))
            try:
                self.collection = client.get_collection("codebase")
            except Exception:
                self.collection = None

        system_prompt = _build_system_prompt(self.repo_path, self.collection)
        self.messages = [{"role": "system", "content": system_prompt}]

        status = (
            f"Connected to index ({self.collection.count()} files)"
            if self.collection
            else "No index found — run synaptix --path first"
        )
        self.sub_title = f"{self.repo_path}  •  {status}"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        question = event.value.strip()
        if not question:
            return
        event.input.clear()
        self._ask(question)

    @work(thread=True)
    def _ask(self, question: str) -> None:
        context, trace = self._retrieve_context(question)

        user_content = question
        if context:
            user_content = f"Relevant source code:\n\n{context}\n\nQuestion: {question}"

        self.messages.append({"role": "user", "content": user_content})

        user_widget = ChatMessage(f"**You:** {question}")
        user_widget.add_class("user-msg")
        chat_view = self.query_one("#chat-view")
        self.call_from_thread(chat_view.mount, user_widget)

        # Show debug trace
        if trace:
            trace_md = "**🔍 Retrieval trace:**\n" + trace
            trace_widget = ChatMessage(trace_md)
            trace_widget.add_class("trace-msg")
            self.call_from_thread(chat_view.mount, trace_widget)

        assistant_widget = ChatMessage("**Synaptix:** ")
        assistant_widget.add_class("assistant-msg")
        self.call_from_thread(chat_view.mount, assistant_widget)

        full_response = ""
        try:
            stream = ollama.chat(
                model="qwen3",
                messages=self.messages,
                stream=True,
            )
            for chunk in stream:
                token = chunk["message"]["content"]
                full_response += token
                self.call_from_thread(
                    assistant_widget.update,
                    f"**Synaptix:** {full_response}",
                )
            self.call_from_thread(chat_view.scroll_end)
        except Exception as e:
            full_response = f"Error: {e}"
            self.call_from_thread(
                assistant_widget.update,
                f"**Synaptix:** {full_response}",
            )

        self.messages.append({"role": "assistant", "content": full_response})

    def _retrieve_context(self, question: str, n_results: int = 6) -> tuple[str, str]:
        if not self.collection or self.collection.count() == 0:
            return "", ""
        results = self.collection.query(
            query_texts=[question], n_results=n_results, include=["documents", "metadatas", "distances"],
        )
        chunks: list[str] = []
        trace_lines: list[str] = []
        seen: set[str] = set()
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0], strict=False,
        ):
            path = meta.get("path", "unknown")
            sym = meta.get("symbol_name", "")
            kind = meta.get("symbol_kind", "file")
            start = meta.get("start_line", 0)
            end = meta.get("end_line", 0)

            key = f"{path}::{sym}" if sym else path
            if key in seen:
                continue
            seen.add(key)

            # Read fresh source from disk for the exact line range
            full_path = Path(self.repo_path) / path
            try:
                lines = full_path.read_text().splitlines()
                source = "\n".join(lines[start : end + 1])
            except (FileNotFoundError, UnicodeDecodeError):
                source = doc[:3000]

            header = f"--- {path}"
            if sym:
                header += f" | {kind} `{sym}` (L{start + 1}-{end + 1})"
            header += " ---"
            chunks.append(f"{header}\n{source}")

            # Build trace line
            loc = f"`{path}`"
            if sym:
                loc = f"`{path}` → {kind} **{sym}** (L{start + 1}–{end + 1})"
            trace_lines.append(f"- {loc}  · distance: `{dist:.4f}`")

        trace = "\n".join(trace_lines) if trace_lines else ""
        return "\n\n".join(chunks), trace


def run_tui(repo_path: str) -> None:
    """Launch the interactive TUI."""
    app = SynaptixChat(repo_path)
    app.run()
