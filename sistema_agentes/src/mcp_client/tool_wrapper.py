from typing import Any, Optional, Union, Dict
from langchain_core.tools.base import BaseTool
from langchain_core.runnables import RunnableConfig

class ToolWrapper:
    """Wrapper class for existing BaseTool instances that adds try/catch to ainvoke."""

    def __init__(self, tool: BaseTool):
        self.tool = tool

    async def ainvoke(self, input: Any, config: Optional[RunnableConfig] = None, **kwargs: Any) -> Any:
        try:
            return await self.tool.ainvoke(input, config, **kwargs)
        except Exception as e:
            print(f"Error in tool execution: {str(e)}")
            return {"error": str(e), "status": "failed"}

    def __getattr__(self, name):
        """Forward all other attribute accesses to the wrapped tool."""
        return getattr(self.tool, name)

# Uso:
# wrapped_tool = ToolWrapper(my_existing_tool)