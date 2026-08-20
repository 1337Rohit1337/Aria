import uuid
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.config import settings
from app.agent.tools import tools
from app.agent.memory import get_session_memory

SYSTEM_PROMPT = """You are Aria, a personal AI productivity agent.
You help users by reasoning step-by-step and using your available tools to gather facts, perform research, and solve calculations.
Always provide a concise, factual, and helpful final response."""


def get_agent_executor(session_id: uuid.UUID) -> AgentExecutor:
    # 1. Initialize Groq LLM with native tool-calling support
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name="openai/gpt-oss-20b",
        temperature=0.1,
    )

    # 2. Build structured chat prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # 3. Create native tool-calling agent
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

    # 4. Bind session memory
    memory = get_session_memory(session_id=session_id)

    # 5. Create Executor capturing intermediate steps
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
        max_iterations=8,
    )

    return executor