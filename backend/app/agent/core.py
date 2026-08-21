"""
Aria Agent Core Configuration.
Sets up the LangChain Tool-Calling Agent with:
- Dynamic 7-tool registry (with injected DB sessions)
- Long-term memory context injection via System Prompt
"""

import uuid
from typing import List

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.agent.tools.registry import get_all_tools

SYSTEM_PROMPT = """You are Aria, a personal AI productivity agent.
You help users by reasoning step-by-step and using your available tools to gather facts, perform research, and solve calculations.

These are relevant past memories, facts, or notes saved from prior conversations:
{long_term_context}

Utilize this context if it is helpful for answering the user's request. 
Always provide a concise, factual, and helpful final response."""


def get_agent_executor(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> AgentExecutor:
    """
    Builds and returns an AgentExecutor instance configured for the specific session.
    """
    
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name="openai/gpt-oss-120b",
        temperature=0.1,
        
    )

    # 2. Get dynamically-constructed tools bound to the current DB session
    tools = get_all_tools(db, session_id)

    # 3. Prompt setup with short-term (chat_history) and long-term (long_term_context) injections
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # 4. Create native tool-calling agent
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

    # 5. Create AgentExecutor 
    # (Memory is handled manually in the route for full async support)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
        max_iterations=8,
    )

    return executor