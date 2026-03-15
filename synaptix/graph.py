from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from synaptix.agents.context_climber import climb
from synaptix.agents.discovery import discover
from synaptix.agents.relationship_resolver import resolve
from synaptix.agents.semantic_indexer import index
from synaptix.renderer import render


class SynaptixState(TypedDict, total=False):
    repo_path: str
    discovered_files: list[str]
    entry_points: list[str]
    dependency_edges: dict[str, list[str]]
    file_labels: dict[str, str]
    mermaid_output: str
    output_file: str


def build_graph() -> StateGraph:
    g = StateGraph(SynaptixState)

    g.add_node("discover", discover)
    g.add_node("climb", climb)
    g.add_node("index", index)
    g.add_node("resolve", resolve)
    g.add_node("render", render)

    g.add_edge(START, "discover")
    g.add_edge("discover", "climb")
    g.add_edge("climb", "index")
    g.add_edge("index", "resolve")
    g.add_edge("resolve", "render")
    g.add_edge("render", END)

    return g.compile()
