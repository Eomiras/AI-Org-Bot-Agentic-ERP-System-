from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # The 'messages' key tracks the conversation history.
    # 'operator.add' ensures that when a node returns messages, they are APPENDED to the list, not overwritten.
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # 'next' tracks which node should execute next.
    next: str
