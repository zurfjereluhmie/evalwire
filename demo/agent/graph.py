"""Demo RAG pipeline built with LangGraph.

Graph topology:
    START → retrieve → generate → END

- ``retrieve``: keyword search over an in-memory corpus, returns the top-K
  document titles most relevant to the user query.
- ``generate``: calls OpenAI via ``init_chat_model`` to produce a short answer
  grounded in the retrieved context.

The graph is intentionally minimal so the demo focuses on evalwire, not on
building a production-grade retrieval system.
"""

import operator
from dataclasses import dataclass, field
from typing import Annotated

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

CORPUS: list[dict] = [
    # sports
    {
        "title": "Introduction to Football",
        "body": "Football is played between two teams of eleven players on a rectangular field.",
    },
    {
        "title": "History of Basketball",
        "body": "Basketball was invented in 1891 by Dr. James Naismith.",
    },
    {
        "title": "Tennis Grand Slams",
        "body": "The four Grand Slams are the Australian Open, French Open, Wimbledon, and US Open.",
    },
    {
        "title": "Olympic Games History",
        "body": "The modern Olympic Games started in Athens in 1896 and are held every four years.",
    },
    # tech
    {
        "title": "How Neural Networks Work",
        "body": "Neural networks are computational models loosely inspired by the human brain.",
    },
    {
        "title": "Introduction to Kubernetes",
        "body": "Kubernetes is an open-source system for automating deployment of containerised applications.",
    },
    {
        "title": "Python Programming Language",
        "body": "Python is a high-level, interpreted programming language emphasising code readability.",
    },
    {
        "title": "Large Language Models",
        "body": "LLMs are deep learning models trained on vast text corpora to generate human-like text.",
    },
    # cooking
    {
        "title": "French Cuisine Basics",
        "body": "French cuisine is characterised by its use of fresh ingredients and classical techniques.",
    },
    {
        "title": "Pasta from Scratch",
        "body": "Homemade pasta requires flour, eggs, and a pasta machine or rolling pin.",
    },
    {
        "title": "Baking Bread at Home",
        "body": "Bread baking requires flour, water, yeast, and salt, plus time for proofing.",
    },
    {
        "title": "Vegetarian Recipes",
        "body": "Vegetarian cooking avoids meat and focuses on vegetables, legumes, grains, and dairy.",
    },
    # travel
    {
        "title": "Backpacking South-East Asia",
        "body": "South-East Asia is popular with backpackers for its affordable hostels, street food and temples.",
    },
    {
        "title": "European Rail Travel",
        "body": "Interrail and Eurail passes allow unlimited train travel across most European countries.",
    },
    {
        "title": "Travelling to Japan",
        "body": "Japan is known for its bullet trains, cherry blossoms, and rich cultural heritage.",
    },
    {
        "title": "Budget Travel Tips",
        "body": "To travel cheaply: book flights early, use public transport and stay in hostels.",
    },
]


@dataclass
class RAGState:
    """Shared state for the RAG pipeline."""

    messages: Annotated[list, operator.add] = field(default_factory=list)
    # Retrieved document titles (populated by the retrieve node)
    retrieved_titles: list[str] = field(default_factory=list)
    # Final generated answer (populated by the generate node)
    answer: str = ""


def retrieve(state: RAGState) -> dict:
    """Keyword-match the user query against the in-memory corpus.

    Returns the top-5 document titles sorted by the number of query words
    found in the document body.
    """
    query = state.messages[-1].content.lower()
    query_words = set(query.split())

    scored = []
    for doc in CORPUS:
        body_words = set(doc["body"].lower().split())
        title_words = set(doc["title"].lower().split())
        overlap = len(query_words & (body_words | title_words))
        scored.append((overlap, doc["title"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_titles = [title for _, title in scored[:5] if _ > 0] or [scored[0][1]]

    return {"retrieved_titles": top_titles}


def generate(state: RAGState) -> dict:
    """Call the LLM to produce a grounded answer from the retrieved context."""
    llm = init_chat_model("gpt-4.1-mini", model_provider="openai")

    context = "\n".join(f"- {t}" for t in state.retrieved_titles)
    user_query = state.messages[-1].content

    messages = [
        SystemMessage(
            content=(
                "You are a helpful assistant. Answer the user question concisely "
                "using only the context below.\n\nContext:\n" + context
            )
        ),
        HumanMessage(content=user_query),
    ]

    response = llm.invoke(messages)
    return {"answer": response.content}


def build_rag_graph() -> CompiledStateGraph:
    """Compile and return the RAG StateGraph."""
    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


if __name__ == "__main__":
    import asyncio

    rag = build_rag_graph()
    result = asyncio.run(
        rag.ainvoke(
            RAGState(messages=[HumanMessage(content="What is a large language model?")])
        )
    )
    print("Retrieved:", result["retrieved_titles"])
    print("Answer   :", result["answer"])
