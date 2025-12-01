import asyncio
from langchain_core.messages import HumanMessage
from app.lib.provider import get_graph


async def test_graph_query(question: str):
    test_state = {
        "messages": [HumanMessage(content=question)],
        "trip_context": None,
        "query": None,
        "query_type": None,
        "needs_visa_api": False,
        "needs_web_search": False,
        "needs_rag": False,
        "rag_results": None,
        "web_results": None,
        "visa_results": None,
        "sources_used": [],
        "relevance_passed": False,
        "retry_count": 0,
    }

    graph = get_graph()
    result = await graph.ainvoke(
        test_state,
        config={"configurable": {"thread_id": "test-123"}},
    )

    print(f"\n{'='*50}")
    print(f"Query type: {result.get('query_type')}")
    print(f"Sources used: {result.get('sources_used')}")
    print(f"Relevance passed: {result.get('relevance_passed')}")
    print(f"Retry count: {result.get('retry_count')}")
    print(f"\nFinal answer:\n{result['messages'][-1].content}")
    print(f"{'='*50}")


if __name__ == "__main__":
    # Test different questions
    asyncio.run(test_graph_query("Can I bring liquids in my carry-on?"))
    # asyncio.run(test_graph_query("Do I need a visa from Korea to USA?"))
    # asyncio.run(test_graph_query("What's the weather in Seoul?"))
