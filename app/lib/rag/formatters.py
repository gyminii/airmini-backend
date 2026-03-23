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
        content = result.get("content", "")
        if len(content) > 600:
            content = content[:600] + "..."
        formatted.append(f"[Result {i}] {result.get('title', 'Untitled')}")
        formatted.append(f"URL: {result.get('url', '')}")
        formatted.append(f"{content}\n")

    return formatted


def format_visa_sources(visa_results: Optional[Dict]) -> List[str]:
    """Format visa API results for LLM context"""
    if not visa_results:
        return ["Visa information not available."]

    if visa_results.get("status") == "incomplete":
        return [f"\n=== Visa Requirements ===\n{visa_results.get('message', '')}"]

    formatted = ["\n=== Visa Requirements ==="]

    # Map common RapidAPI visa response fields to readable labels
    field_labels = {
        "visa": "Visa required",
        "visa_required": "Visa required",
        "passport": "Passport country",
        "destination": "Destination country",
        "dur": "Allowed stay",
        "stay_duration": "Allowed stay",
        "admission_refused": "Admission refused",
        "visa_on_arrival": "Visa on arrival",
        "e_visa": "E-visa available",
        "notes": "Notes",
        "category": "Visa category",
    }

    for key, label in field_labels.items():
        value = visa_results.get(key)
        if value is not None and value != "":
            formatted.append(f"- {label}: {value}")

    # Include any remaining fields not in the map
    known_keys = set(field_labels.keys())
    for key, value in visa_results.items():
        if key not in known_keys and value is not None and value != "":
            formatted.append(f"- {key}: {value}")

    return formatted
