import json
from typing import Optional, Dict, List


def format_rag_sources(rag_results: Optional[List[dict]]) -> List[str]:
    """Format RAG results for LLM context"""
    if not rag_results:
        return ["No relevant information in knowledge base."]

    formatted = ["=== Knowledge Base ==="]
    for i, result in enumerate(rag_results, 1):
        source = (
            result["source"].rsplit("/", 1)[-1]
            if "/" in result["source"]
            else result["source"]
        )
        formatted.append(f"\n[Source {i} - {source}]")
        formatted.append(result["content"])

    return formatted


def format_web_sources(web_results: Optional[Dict]) -> List[str]:
    """Format web search results for LLM context"""
    if not web_results:
        return ["Web search returned no results."]

    formatted = ["\n=== Web Search ==="]

    if web_results.get("answer"):
        formatted.append(f"Summary: {web_results['answer']}\n")

    for i, result in enumerate(web_results.get("results", [])[:3], 1):
        formatted.append(f"[Result {i}] {result.get('title', 'Untitled')}")
        formatted.append(f"{result.get('content', '')[:300]}...\n")

    return formatted


def format_visa_sources(visa_results: Optional[Dict]) -> List[str]:
    """Format visa API results for LLM context"""
    if not visa_results:
        return ["Visa information not available."]

    formatted = ["\n=== Visa Requirements ==="]
    formatted.append(json.dumps(visa_results, indent=2))

    return formatted
