"""模块基类 - 所有功能模块继承此类"""
from abc import ABC, abstractmethod
from langchain_core.tools import BaseTool


class BaseModule(ABC):
    module_id: str = ""
    display_name: str = ""
    description: str = ""
    default_config: dict = {}

    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        """返回该模块的 LangChain tools"""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """返回子 agent 的 system prompt"""
        ...

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass
