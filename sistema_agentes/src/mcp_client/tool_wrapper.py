from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool


def patch_tool_with_exception_handling(tool: BaseTool) -> BaseTool:
    original_ainvoke = tool.ainvoke

    async def wrapped_ainvoke(*args, **kwargs):
        try:
            return await original_ainvoke(*args, **kwargs)
        except Exception as e:
            error =  f"Exception ocurred executing tool {tool.name}: {str(e)}"

            # Obtener id de la llamada
            tool_call_id = args[0].get("id")
            if not tool_call_id:
                tool_call_id = ""

            return ToolMessage(
                content=error,
                tool_call_id=tool_call_id,
            )

    object.__setattr__(tool, 'ainvoke', wrapped_ainvoke)
    return tool
