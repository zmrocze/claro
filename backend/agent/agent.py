"""
LangGraph agent implementation with Zep memory integration
"""

import itertools
import logging
import os
import uuid
from typing import Callable, Optional
from langchain_core.runnables import Runnable
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import BaseMessage

from langchain_core.messages import (
  AIMessage,
  SystemMessage,
  HumanMessage,
  trim_messages,
)
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from pydantic import SecretStr

from backend.agent.state import AgentState
from backend.agent.tools import mock_action
from backend.config import (
  AppConfig,
  get_grok_api_key,
  GROK_API_BASE_URL,
)
from backend.exceptions import AppError
from backend.memory import create_memory_provider
from backend.memory.base import MemoryProvider

logger = logging.getLogger(__name__)


def agent_error_from_exception(
  e: Exception,
  name: str = "AGENT_ERROR",
  context: Optional[str] = None,
) -> AppError:
  """Helper function to create agent errors from exceptions"""
  return AppError.from_exception(
    e=e,
    name=name,
    source="agent",
    context=context,
  )


def system_content_user(context: str):
  # Build system message with context
  system_content = f"""You are Claro, a helpful and personalized AI assistant.
    You have access to context about the user from past conversations.
    Use this context to provide personalized and relevant responses.
    If you need to search for specific information from past conversations, use the search tools available to you.
    
    User Context:
    {context if context else "No prior context available."}
    
    Keep responses conversational, helpful, and empathetic."""
  return system_content


def system_content_tool(context: str):
  return system_content_user(context)


def create_grok_llm(tools: list) -> Runnable[LanguageModelInput, BaseMessage]:
  """Create Grok LLM instance with tools"""
  return ChatOpenAI(
    api_key=SecretStr(get_grok_api_key()),
    base_url=GROK_API_BASE_URL,
    model=AppConfig.LLM_MODEL,
    temperature=AppConfig.LLM_TEMPERATURE,
    max_completion_tokens=AppConfig.LLM_MAX_TOKENS,
  ).bind_tools(tools)


def create_mock_llm(tools: list) -> Runnable[LanguageModelInput, BaseMessage]:
  """Create mock LLM instance with tools (for testing)"""
  return GenericFakeChatModel(
    messages=itertools.cycle([AIMessage(content="Mock response")])
  )


def response_and_should_continue(response: AIMessage) -> Command:
  if not response.tool_calls:
    next_node = "end"
  # Otherwise continue to tools
  else:
    next_node = "agent_after_tools"

  return Command(
    update={"messages": [response]},
    goto=next_node,
  )


class CarloAgent:
  """LangGraph agent with memory integration via MemoryProvider abstraction"""

  def __init__(
    self,
    user_id: str,
    memory_provider: MemoryProvider,
    first_name: str,
    last_name: str,
    llm_factory: Callable[[list], Runnable[LanguageModelInput, BaseMessage]],
  ):
    """
    Initialize the Claro agent

    Args:
      user_id: Unique user identifier
      memory_provider: Initialized memory provider implementation
      first_name: User's first name
      last_name: User's last name
      llm_factory: Function that takes tools and returns configured LLM
    """
    self.user_id = user_id
    self.first_name = first_name
    self.last_name = last_name
    self.memory = memory_provider

    # Configure LangSmith tracing if enabled
    if AppConfig.LANGCHAIN_TRACING_V2 and AppConfig.LANGSMITH_API_KEY:
      os.environ["LANGCHAIN_TRACING_V2"] = "true"
      os.environ["LANGCHAIN_PROJECT"] = AppConfig.LANGSMITH_PROJECT
      os.environ["LANGSMITH_API_KEY"] = AppConfig.LANGSMITH_API_KEY
      logger.info(
        f"LangSmith tracing enabled for project: {AppConfig.LANGSMITH_PROJECT}"
      )

    # Create single thread for this user (as per app_technical.md)
    # Single, sequential conversation thread for the app instance
    self.memory.create_or_get_user(
      user_id=user_id,
      first_name=self.first_name,
      last_name=self.last_name,
      email=AppConfig.ZEP_USER_EMAIL,
    )

    # Create or use existing thread (single thread per user)
    if not self.memory.current_thread_id:
      self.thread_id = self.memory.create_thread(user_id=user_id)
    else:
      self.thread_id = self.memory.current_thread_id

    logger.info(f"Agent using thread: {self.thread_id}")

    # Create tools - memory provider handles tool creation
    memory_tools = self.memory.create_memory_search_tools(user_id)
    self.tools = [*(memory_tools if memory_tools else []), mock_action]

    # Initialize LLM using factory
    self.llm = llm_factory(self.tools)

    # Build the graph
    self.graph = self._build_graph()

    logger.info(f"Claro agent initialized for user {user_id}")

  # Define the chatbot node
  async def chatbot_node(self, state: AgentState, system_content: Callable[[str], str]):
    """Main chatbot logic with memory integration"""
    try:
      context = self.memory.get_context(thread_id=self.thread_id, mode="basic")
      if context is None:
        context = ""

      system_message = SystemMessage(content=system_content(context))
      messages = [system_message] + state["messages"]

      response = await self.llm.ainvoke(messages)

      # Add assistant response
      try:
        self.memory.add_message(
          content=response.content
          if isinstance(response.content, str)
          else str(response.content),
          role="assistant",
          name="Claro",
          thread_id=self.thread_id,
        )
        logger.debug(f"Added messages to thread {self.thread_id}")
      except Exception as e:
        logger.warning(f"Failed to add assistant message to memory: {e}")

      # Truncate message history to prevent unbounded growth
      # Keep last 10 messages in state (Zep maintains full history)
      state["messages"] = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=len,
        max_tokens=10,
        start_on="human",
        end_on=("human", "tool"),
        include_system=False,
      )

      assert isinstance(response, AIMessage)
      return response_and_should_continue(response)

    except Exception as e:
      logger.error(f"Error in chatbot node: {e}", exc_info=True)
      raise agent_error_from_exception(
        e=e,
        name="CHATBOT_NODE_ERROR",
        context="Error processing your request in chatbot node",
      )

  def _build_graph(self):
    """Build the LangGraph state graph"""

    # Define the chatbot node
    async def chatbot_answer_user(state: AgentState):
      """Main chatbot logic with memory integration"""

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

      # Get response from LLM
      return await self.chatbot_node(state, system_content_user)

    # Define the chatbot node
    async def chatbot_answer_tool(state: AgentState):
      """Main chatbot logic with memory integration"""
      # not adding tool responses to zep memory

      # Get response from LLM
      return await self.chatbot_node(state, system_content_tool)

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
    graph_builder.add_node("agent", chatbot_answer_user)
    graph_builder.add_node("agent_after_tools", chatbot_answer_tool)
    graph_builder.add_node("tools", tool_node)

    # Add edges
    graph_builder.add_edge(START, "agent")
    # graph_builder.add_conditional_edges(
    #   "agent", should_continue, {"continue": "tools", "end": END}
    # )
    graph_builder.add_edge("tools", "agent_after_tools")
    # graph_builder.add_conditional_edges(
    #   "agent_after_tools", should_continue, {"continue": "tools", "end": END}
    # )

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

      raise agent_error_from_exception(
        e=Exception("Agent failed to generate a response"),
        name="NO_RESPONSE_GENERATED",
        context="Agent invocation did not produce a valid response",
      )

    except Exception as e:
      logger.error(f"Error invoking agent: {e}", exc_info=True)
      raise agent_error_from_exception(
        e=e,
        name="AGENT_INVOCATION_ERROR",
        context="Error invoking agent",
      )

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
      raise agent_error_from_exception(
        e=e,
        name="AGENT_STREAMING_ERROR",
        context="Error streaming response from agent",
      )


def new_agent(
  user_id: Optional[str] = None,
  first_name: Optional[str] = None,
  last_name: Optional[str] = None,
  memory_provider: Optional[MemoryProvider] = None,
  llm_factory: Optional[
    Callable[[list], Runnable[LanguageModelInput, BaseMessage]]
  ] = None,
) -> CarloAgent:
  """
  Create a new CarloAgent instance with initialized memory provider.
  This function handles all the initialization logic including:
  - Creating memory provider from config if not provided
  - Resolving user_id from config or generating one
  - Creating LLM factory based on LLM_PROVIDER config
  - Initializing the agent with all dependencies

  Args:
    user_id: User ID (will use config or generate if not provided)
    first_name: User's first name
    last_name: User's last name
    memory_provider: Optional pre-initialized memory provider (will create from config if not provided)
    llm_factory: Optional LLM factory function (will create from config if not provided)

  Returns:
    Initialized CarloAgent instance
  """
  # Resolve all config defaults in one place
  resolved_user_id = (
    user_id or AppConfig.ZEP_USER_ID or f"carlo_user_{uuid.uuid4().hex[:8]}"
  )
  if "carlo_user_" in resolved_user_id and not user_id:
    logger.info(f"Generated user ID: {resolved_user_id}")

  resolved_memory = memory_provider or create_memory_provider()
  resolved_first_name = first_name or AppConfig.ZEP_USER_FIRST_NAME
  resolved_last_name = last_name or AppConfig.ZEP_USER_LAST_NAME

  # Resolve LLM factory based on config
  if llm_factory is None:
    provider = AppConfig.LLM_PROVIDER.lower()
    if provider == "grok":
      resolved_llm_factory = create_grok_llm
    elif provider == "mock":
      resolved_llm_factory = create_mock_llm
    else:
      raise AppError(
        description=f"Unknown LLM_PROVIDER: {provider}. Expected 'grok' or 'mock'",
        name="CONFIG_ERROR",
        source="agent",
      )
  else:
    resolved_llm_factory = llm_factory

  # Create agent with fully resolved values
  agent = CarloAgent(
    user_id=resolved_user_id,
    memory_provider=resolved_memory,
    first_name=resolved_first_name,
    last_name=resolved_last_name,
    llm_factory=resolved_llm_factory,
  )

  logger.info(f"Agent created with thread: {agent.thread_id}")
  return agent


# Singleton agent instance
_agent_instance: Optional[CarloAgent] = None


async def get_agent() -> CarloAgent:
  """
  Get or create the singleton agent instance.
  Uses config defaults for all values.

  Returns:
    CarloAgent instance
  """
  global _agent_instance

  if _agent_instance is None:
    _agent_instance = new_agent()

  return _agent_instance
