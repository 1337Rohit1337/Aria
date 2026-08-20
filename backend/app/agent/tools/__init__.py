from app.agent.tools.web_search import web_search
from app.agent.tools.calculator import calculator

tools = [web_search, calculator]

__all__ = ["web_search", "calculator", "tools"]