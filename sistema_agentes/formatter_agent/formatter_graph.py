from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.BaseAgent import AgentState, BaseAgent


class FormatterAgent(BaseAgent):
    def __init__(
            self,
            model: BaseChatModel = ChatOpenAI(model="gpt4-o-mini"),
            debug: bool = True
                 ):
        super().__init__(
            name="formatter_agent",
            model=model,
            debug=debug
                         )

