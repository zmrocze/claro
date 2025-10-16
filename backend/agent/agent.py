"""
LangGraph agent implementation with Zep memory integration
"""

import logging
import os
import uuid
from typing import Optional

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, trim_messages
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message as ZepMessage

from backend.agent.state import AgentState
from backend.agent.tools import create_zep_tools, mock_action
from backend.config import AppConfig, get_grok_api_key, GROK_API_BASE_URL
from backend.memory import get_memory_client
from backend.memory.base import MemoryProvider
from zep_cloud.client import AsyncZep
from backend.config import get_zep_api_key

logger = logging.getLogger(__name__)


class CarloAgent:
  """LangGraph agent with memory integration via MemoryProvider abstraction"""
  
  def __init__(
    self,
    user_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    memory_provider: Optional[MemoryProvider] = None,
  ):
    """
    Initialize the Carlo agent
    
    Args:
      user_id: Unique user identifier
      first_name: User's first name
      last_name: User's last name
      memory_provider: Memory provider implementation (uses default if not provided)
    """
    self.user_id = user_id
    self.first_name = first_name or AppConfig.ZEP_USER_FIRST_NAME
    self.last_name = last_name or AppConfig.ZEP_USER_LAST_NAME
    
    # Configure LangSmith tracing if enabled
    if AppConfig.LANGCHAIN_TRACING_V2 and AppConfig.LANGSMITH_API_KEY:
      os.environ["LANGCHAIN_TRACING_V2"] = "true"
      os.environ["LANGCHAIN_PROJECT"] = AppConfig.LANGSMITH_PROJECT
      os.environ["LANGSMITH_API_KEY"] = AppConfig.LANGSMITH_API_KEY
      logger.info(f"LangSmith tracing enabled for project: {AppConfig.LANGSMITH_PROJECT}")
    
    # Use provided memory provider or get default
    self.memory = memory_provider or get_memory_client()
    
    # Create single thread for this user (as per app_technical.md)
    # Single, sequential conversation thread for the app instance
    self.memory.create_or_get_user(
      user_id=user_id,
      first_name=self.first_name,
      last_name=self.last_name,
      email=AppConfig.ZEP_USER_EMAIL
    )
    
    # Create or use existing thread (single thread per user)
    if not self.memory.current_thread_id:
      self.thread_id = self.memory.create_thread(user_id=user_id)
    else:
      self.thread_id = self.memory.current_thread_id
    
    logger.info(f"Agent using thread: {self.thread_id}")
    
    # Create tools - needs async Zep client for search
    # We use the underlying client for tool operations only
    zep_key = get_zep_api_key()
    self._zep_async_client = AsyncZep(
      api_key=zep_key if zep_key else None,
      base_url=AppConfig.ZEP_API_URL
    )
    zep_tools = create_zep_tools(self._zep_async_client, user_id)
    self.tools = [*zep_tools, mock_action]
    
    # Initialize LLM
    self.llm = ChatOpenAI(
      api_key=get_grok_api_key(),
      base_url=GROK_API_BASE_URL,
      model=AppConfig.LLM_MODEL,
      temperature=AppConfig.LLM_TEMPERATURE,
      max_completion_tokens=AppConfig.LLM_MAX_TOKENS,
    ).bind_tools(self.tools)
    
    # Build the graph
    self.graph = self._build_graph()
    
    logger.info(f"Carlo agent initialized for user {user_id}")
  
  def _build_graph(self):
    """Build the LangGraph state graph"""
    
    # Define the chatbot node
    async def chatbot(state: AgentState):
      """Main chatbot logic with memory integration"""
      try:
        # Get context from memory provider
        # Uses single thread per user as per app_technical.md
        context = self.memory.get_context(
          thread_id=self.thread_id,
          mode="basic"
        )
        
        # Build system message with context
        system_content = f"""You are Carlo, a helpful and personalized AI assistant.
You have access to context about the user from past conversations.
Use this context to provide personalized and relevant responses.
If you need to search for specific information from past conversations, use the search tools available to you.

User Context:
{context if context else "No prior context available."}

Keep responses conversational, helpful, and empathetic."""
        
        system_message = SystemMessage(content=system_content)
        
        # Prepare messages for LLM
        messages = [system_message] + state["messages"]
        
        # Get response from LLM
        response = await self.llm.ainvoke(messages)
        
        # Save messages using memory provider
        # Uses single thread per user
        user_message = state["messages"][-1]
        
        # Add user message
        try:
          self.memory.add_message(
            content=user_message.content,
            role="user",
            name=f"{state['first_name']} {state['last_name']}",
            thread_id=self.thread_id,
          )
        except Exception as e:
          logger.warning(f"Failed to add user message to memory: {e}")
        
        # Add assistant response
        try:
          self.memory.add_message(
            content=response.content if isinstance(response.content, str) else str(response.content),
            role="assistant",
            name="Carlo",
            thread_id=self.thread_id,
          )
          logger.debug(f"Added messages to thread {self.thread_id}")
        except Exception as e:
          logger.warning(f"Failed to add assistant message to memory: {e}")
        
        # Truncate message history to prevent unbounded growth
        # Keep last 5 messages in state (Zep maintains full history)
        state["messages"] = trim_messages(
          state["messages"],
          strategy="last",
          token_counter=len,
          max_tokens=5,
          start_on="human",
          end_on=("human", "tool"),
          include_system=False,
        )
        
        return {"messages": [response]}
        
      except Exception as e:
        logger.error(f"Error in chatbot node: {e}", exc_info=True)
        error_response = AIMessage(
          content="I apologize, but I encountered an error processing your request. Please try again."
        )
        return {"messages": [error_response]}
    
    # Define conditional edge logic
    async def should_continue(state, config):
      """Determine whether to continue to tools or end"""
      messages = state["messages"]
      last_message = messages[-1]
      
      # If there are no tool calls, end
      if not last_message.tool_calls:
        return "end"
      # Otherwise continue to tools
      else:
        return "continue"
    
    # Build the graph
    graph_builder = StateGraph(AgentState)
    
    # Add nodes
    tool_node = ToolNode(self.tools)
    graph_builder.add_node("agent", chatbot)
    graph_builder.add_node("tools", tool_node)
    
    # Add edges
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges(
      "agent",
      should_continue,
      {"continue": "tools", "end": END}
    )
    graph_builder.add_edge("tools", "agent")
    
    # Compile with checkpointer for persistence
    memory = MemorySaver()
    return graph_builder.compile(checkpointer=memory)
  
  async def ainvoke(
    self,
    message: str,
  ) -> str:
    """
    Invoke the agent with a message
    Uses single thread per user (app_technical.md requirement)
    
    Args:
      message: User message
      
    Returns:
      Agent's response
    """
    try:
      result = await self.graph.ainvoke(
        {
          "messages": [HumanMessage(content=message)],
          "thread_id": self.thread_id,
          "user_id": self.user_id,
          "first_name": self.first_name,
          "last_name": self.last_name,
        },
        config={"configurable": {"thread_id": self.thread_id}},
      )
      
      # Extract the last message (agent's response)
      if result and result.get("messages"):
        last_message = result["messages"][-1]
        if isinstance(last_message, AIMessage):
          return str(last_message.content)
      
      return "I apologize, but I couldn't generate a response."
      
    except Exception as e:
      logger.error(f"Error invoking agent: {e}", exc_info=True)
      return f"I apologize, but I encountered an error: {str(e)}"
  
  async def astream(
    self,
    message: str,
  ):
    """
    Stream the agent's response
    Uses single thread per user
    
    Args:
      message: User message
      
    Yields:
      Chunks of the agent's response
    """
    try:
      async for chunk in self.graph.astream(
        {
          "messages": [HumanMessage(content=message)],
          "thread_id": self.thread_id,
          "user_id": self.user_id,
          "first_name": self.first_name,
          "last_name": self.last_name,
        },
        config={"configurable": {"thread_id": self.thread_id}},
      ):
        yield chunk
        
    except Exception as e:
      logger.error(f"Error streaming from agent: {e}", exc_info=True)
      yield {"error": str(e)}


# Singleton agent instance
_agent_instance: Optional[CarloAgent] = None


async def get_agent(
  user_id: Optional[str] = None,
  first_name: Optional[str] = None,
  last_name: Optional[str] = None,
) -> CarloAgent:
  """
  Get or create the singleton agent instance
  
  Args:
    user_id: User ID (will use config or generate if not provided)
    first_name: User's first name
    last_name: User's last name
    
  Returns:
    CarloAgent instance
  """
  global _agent_instance
  
  if _agent_instance is None:
    # Use configured user ID or generate one
    if user_id is None:
      user_id = AppConfig.ZEP_USER_ID
      if user_id is None:
        user_id = f"carlo_user_{uuid.uuid4().hex[:8]}"
        logger.info(f"Generated user ID: {user_id}")
    
    # Create agent
    _agent_instance = CarloAgent(
      user_id=user_id,
      first_name=first_name or AppConfig.ZEP_USER_FIRST_NAME,
      last_name=last_name or AppConfig.ZEP_USER_LAST_NAME,
    )
    
    # User and thread already created in __init__
    logger.info(f"Agent ready with thread: {_agent_instance.thread_id}")
  
  return _agent_instance

