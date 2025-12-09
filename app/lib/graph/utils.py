from langchain_core.messages import HumanMessage
from app.lib.llm import chat_model


async def generate_chat_title(message: str) -> str:
    """Generate a concise title from the first user message"""
    prompt = f"""
    Generate a short, descriptive title (max 6 words) for a chat that starts with this message:
    "{message}"
    
    Return ONLY the title, no quotes, no explanation.
    Examples:
    - "What are TSA liquid rules?" → "TSA Liquid Rules"
    - "Do I need a visa to Japan?" → "Japan Visa Requirements"
    - "Help me pack for Paris" → "Paris Packing Guide"
    """

    response = chat_model.invoke([HumanMessage(content=prompt)])
    title = response.content.strip().strip('"').strip("'")
    return title[:60]
