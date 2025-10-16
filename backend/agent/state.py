"""
Agent state definition for LangGraph
"""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import add_messages


class AgentState(TypedDict):
  """State for the LangGraph agent"""
  
  messages: Annotated[list, add_messages]
  thread_id: str
  user_id: str
  first_name: str
  last_name: str

