from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class MacroCalendarInput(BaseModel):
    check_days: int = Field(30, description="Number of days to check for upcoming events (default: 30)")

class MacroCalendarTool(BaseTool):
    name: str = "Macro Economic Calendar Tool"
    description: str = "Fetches upcoming major economic events (FOMC, CPI, Jobs Report) that could impact market volatility."
    args_schema: Type[BaseModel] = MacroCalendarInput

    def _run(self, check_days: int = 30) -> str:
        try:
            from utils.macro_calendar import get_macro_context
            return get_macro_context()
        except Exception as e:
            return f"Error fetching macro calendar: {str(e)}"
