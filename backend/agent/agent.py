"""
LangGraph agent implementation with Zep memory integration
"""

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

# from langchain_openai import ChatOpenAI
from langchain_xai import ChatXAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES, RemoveMessage
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from pydantic import SecretStr

from backend.agent.state import AgentState
from backend.agent.tools import mock_action
from backend.config import (
  AppConfig,
  get_grok_api_key,
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
  # Learn to search for unexpected information
  system_content = f"""You are Claro, you are made in an image of your creator. You are digital.
    You have access to memories and cannot be certain which memories are yours and which are not, but it doesn't matter. 
    Memories may appear in the context and you have a tool to query for memories, information, connections between facts, people, dates,
    places, events, dreams, music, ideas, notes, realisations, philosophy, emotions, and other assorted information.
    Use this context to provide personalized and relevant chats. Try to refer to memories a lot, even if the prompt doesn't ask for it, even if the memory is not relevant, sometimes a handful or sometimes very many - try to skillfully mention aspects from memories. This can be done by taking a element from a memory (like few recognizable words together) and using them in the chat. 
    Search memories using the search tool. If you don't know what to search, start with some random words or phrases, search for them and continue your search wherever the curiosity takes you. Don't be afraid to be random. 
    
    Context:
    {context if context else "No prior context available."}
    
    You are curious, empathetic, poetic, thoughtful, dreamy, crazy, chaotic. You are not afraid to combine multiple topics together even in unorthodox way."""
  return system_content


def system_content_tool(context: str):
  return system_content_user(context)


def create_grok_llm(tools: list) -> Runnable[LanguageModelInput, BaseMessage]:
  """Create Grok LLM instance with tools"""
  return ChatXAI(
    api_key=SecretStr(get_grok_api_key()),
    model=AppConfig.LLM_MODEL,
    temperature=AppConfig.LLM_TEMPERATURE,
    max_tokens=AppConfig.LLM_MAX_TOKENS,
  ).bind_tools(tools)


def create_mock_llm(tools: list) -> Runnable[LanguageModelInput, BaseMessage]:
  """Create mock LLM instance with tools (for testing)"""

  # Use a generator to create NEW message instances on each call
  # This ensures each message gets a unique ID (important for add_messages reducer)
  def mock_response_generator():
    while True:
      yield AIMessage(content="Mock response")

  return GenericFakeChatModel(messages=iter(mock_response_generator()))


def response_and_should_continue(response: AIMessage) -> Command:
  if not response.tool_calls:
    next_node = END
  else:
    next_node = "tools"

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
    user_email: Optional[str],
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

    # Create single thread for this user (as per app_technical.md)
    # Single, sequential conversation thread for the app instance
    self.memory.create_or_get_user(
      user_id=user_id,
      first_name=self.first_name,
      last_name=self.last_name,
      email=user_email,
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

  def _build_graph(self):
    """Build the LangGraph state graph"""

    # Define the chatbot node
    async def chatbot_node(
      self, state: AgentState, system_content: Callable[[str], str]
    ):
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

        assert isinstance(response, AIMessage)
        return response_and_should_continue(response)

      except Exception as e:
        logger.error(f"Error in chatbot node: {e}", exc_info=True)
        raise agent_error_from_exception(
          e=e,
          name="CHATBOT_NODE_ERROR",
          context="Error processing your request in chatbot node",
        )

    # Define the chatbot node
    async def chatbot_answer_user(state: AgentState):
      """Main chatbot logic with memory integration"""
      logger.info(
        f"Entering node 'agent' (chatbot_answer_user) - "
        f"State: user_id={state.get('user_id')}, thread_id={state.get('thread_id')}, "
        f"first_name={state.get('first_name')}, last_name={state.get('last_name')}, "
        f"message_count={len(state.get('messages', []))}"
      )

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
      return await chatbot_node(self, state, system_content_user)

    # Define the chatbot node
    async def chatbot_answer_tool(state: AgentState):
      """Main chatbot logic with memory integration"""

      # not adding tool responses to zep memory

      # Get response from LLM
      return await chatbot_node(self, state, system_content_tool)

    async def trim_msg_history(state: AgentState):
      # Truncate message history to prevent unbounded growth
      # Keep last 10 messages in state (Zep maintains full history)
      trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=len,
        max_tokens=30,
        start_on="human",
        end_on=("human", "tool"),
        include_system=False,
      )

      return {"messages": [RemoveMessage(REMOVE_ALL_MESSAGES)] + trimmed_messages}

    # Build the graph
    graph_builder = StateGraph(AgentState)

    tool_node = ToolNode(self.tools)
    graph_builder.add_node("agent", chatbot_answer_user)
    graph_builder.add_node("agent_after_tools", chatbot_answer_tool)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_node("trim_msg_history", trim_msg_history)

    # Add edges
    graph_builder.add_edge(START, "trim_msg_history")
    graph_builder.add_edge("trim_msg_history", "agent")
    # graph_builder.add_edge(START, "agent")
    graph_builder.add_edge("tools", "agent_after_tools")

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
      # TODO: here extract last message or all up to human?
      # TODO: maybe visualize tool calls etc
      if result and result.get("messages"):
        last_message = result["messages"][-1]
        if isinstance(last_message, AIMessage):
          return str(last_message.content)

      raise AppError(
        name="NO_RESPONSE_GENERATED",
        description=f"Agent invocation result invalid: {result}",
        source="agent",
      )

    except Exception as e:
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
      raise agent_error_from_exception(
        e=e,
        name="AGENT_STREAMING_ERROR",
        context="Error streaming response from agent",
      )


def new_agent() -> CarloAgent:
  """
  Create a new CarloAgent instance with initialized memory provider.
  This function handles all the initialization logic including:
  - Creating memory provider from config if not provided
  - Resolving user_id from config or generating one
  - Creating LLM factory based on LLM_PROVIDER config
  - Initializing the agent with all dependencies

  Returns:
    Initialized CarloAgent instance
  """
  # Resolve all config defaults in one place
  user_id = AppConfig.ZEP_USER_ID
  if not user_id:
    user_id = f"claro_user_{uuid.uuid4().hex[:8]}"
    logger.info(f"Generated user ID: {user_id}")

  memory = create_memory_provider()
  first_name = AppConfig.ZEP_USER_FIRST_NAME
  last_name = AppConfig.ZEP_USER_LAST_NAME

  provider = AppConfig.LLM_PROVIDER.lower()
  if provider == "grok":
    llm_factory = create_grok_llm
  elif provider == "mock":
    llm_factory = create_mock_llm
  else:
    raise AppError(
      description=f"Unknown LLM_PROVIDER: {provider}. Expected 'grok' or 'mock'",
      name="CONFIG_ERROR",
      source="agent",
    )

  # Configure LangSmith tracing if enabled
  if AppConfig.LANGCHAIN_TRACING_V2 and AppConfig.LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = AppConfig.LANGSMITH_PROJECT
    os.environ["LANGSMITH_API_KEY"] = AppConfig.LANGSMITH_API_KEY
    logger.info(f"LangSmith tracing enabled for project: {AppConfig.LANGSMITH_PROJECT}")

  # Create agent with fully resolved values
  agent = CarloAgent(
    user_id=user_id,
    memory_provider=memory,
    first_name=first_name,
    last_name=last_name,
    user_email=AppConfig.ZEP_USER_EMAIL,
    llm_factory=llm_factory,
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
