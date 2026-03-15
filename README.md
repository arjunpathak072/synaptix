# Synaptix

Agentic AI system that autonomously constructs a **Mental Map** of any Python repository. It discovers entry points, traces import dependencies via AST parsing, uses a local LLM to semantically label each module, and outputs a Mermaid.js dependency flowchart.

Built with **LangGraph** (multi-agent orchestration), **Ollama/qwen3** (local LLM), and **ChromaDB** (vector storage).

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
# Analyze a Python repository
python -m synaptix --path /path/to/python/repo

# Analyze the current directory
python -m synaptix --path .
```

## Output

- Mermaid flowchart printed to terminal
- `synaptix_output.md` saved in the target repo with the embedded Mermaid diagram

## Architecture

```
CLI → Discovery Agent → Context Climber → Semantic Indexer → Relationship Resolver → Mermaid Renderer
```

| Agent | Role |
|---|---|
| **Discovery Agent** | Scans repo for `.py` files, identifies entry points |
| **Context Climber** | AST-based recursive import tracing, builds dependency DAG |
| **Semantic Indexer** | Vectorizes code chunks into ChromaDB for future querying |
| **Relationship Resolver** | Uses Ollama/qwen3 to label each module's role |
| **Mermaid Renderer** | Converts labeled DAG to Mermaid.js flowchart |
