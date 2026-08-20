import numexpr
from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """
    Perform mathematical calculations.
    Input must be a valid numerical/mathematical expression (e.g. '24 * 1.15', '(100 / 3) + 42').
    """
    try:
        clean_expr = expression.strip().replace("^", "**")
        result = numexpr.evaluate(clean_expr).item()
        return str(result)
    except Exception as e:
        return f"Error evaluating expression '{expression}': {str(e)}"