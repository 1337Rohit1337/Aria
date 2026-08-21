import os

from langchain_core.tools import tool, BaseTool
from langchain_community.utilities import OpenWeatherMapAPIWrapper
from langchain_community.tools import OpenWeatherMapQueryRun

from app.config import get_settings


def get_weather_tool() -> BaseTool:
    """Returns real weather tool if API key exists, else a graceful fallback."""
    settings = get_settings()

    if not settings.OPENWEATHERMAP_API_KEY:
        @tool
        def weather(city: str) -> str:
            """Get current weather for a city. Returns temperature, conditions, humidity."""
            return "Weather unavailable: OPENWEATHERMAP_API_KEY not configured."
        return weather

    os.environ["OPENWEATHERMAP_API_KEY"] = settings.OPENWEATHERMAP_API_KEY
    wrapper = OpenWeatherMapAPIWrapper()
    return OpenWeatherMapQueryRun(api_wrapper=wrapper)