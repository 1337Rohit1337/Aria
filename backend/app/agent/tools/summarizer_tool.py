from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings


@tool
def summarize(text: str) -> str:
    """Condense long text into concise bullet points. Use when the user asks for a summary or when you need to compress a large search result."""
    settings = get_settings()

    if len(text) > 6000:
        text = text[:6000] + "\n...[truncated]"

    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize the following text into clear, concise bullet points. No preamble."),
        ("human", "{text}"),
    ])

    chain = prompt | llm
    result = chain.invoke({"text": text})
    return result.content