# Synaptix

Agentic AI system that autonomously constructs a **Mental Map** of any Python repository. It discovers entry points, traces import dependencies via AST parsing, uses a local LLM to semantically label each module, and outputs a Mermaid.js dependency flowchart.

Built with **LangGraph** (multi-agent orchestration), **Ollama/qwen3** (local LLM), **ChromaDB** (vector storage), and **Tree-sitter** (symbol-level code indexing).

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) installed and running

## Setup

```bash
# Pull the LLM model
ollama pull qwen3

# Install Synaptix
pip install -e .
```

## Usage

```bash
# Analyze a Python repository (generates Mermaid diagram)
python -m app --path /path/to/python/repo

# Analyze and launch interactive chat
python -m app --path /path/to/python/repo --chat

# Chat with a previously analyzed repo (skips re-indexing)
python -m app --path /path/to/python/repo --chat
```

If you pass `--chat` and the repo hasn't been indexed yet, Synaptix will automatically run the full analysis pipeline before opening the chat.

## Output

- Mermaid flowchart printed to terminal
- `synaptix_output.md` saved in the target repo with the embedded Mermaid diagram
- `.synaptix_db/` created in the target repo (ChromaDB vector index)

## Interactive Chat

The TUI chat lets you ask natural-language questions about the codebase. Each query shows a **retrieval trace** — the exact symbols, files, line ranges, and vector distances the model used to answer — so you can see what it accessed and why.

## Architecture

```
CLI → Discovery Agent → Context Climber → Semantic Indexer → Relationship Resolver → Mermaid Renderer → [Chat TUI]
```

| Agent | Role |
|---|---|
| **Discovery Agent** | Scans repo for `.py` files, identifies entry points |
| **Context Climber** | AST-based recursive import tracing, builds dependency DAG |
| **Semantic Indexer** | Uses Tree-sitter to extract symbols (functions, classes, methods) and indexes each as a separate vector chunk in ChromaDB |
| **Relationship Resolver** | Uses Ollama/qwen3 to label each module's role |
| **Mermaid Renderer** | Converts labeled DAG to Mermaid.js flowchart |
| **Chat TUI** | Interactive Q&A with symbol-level RAG retrieval and debug trace |
