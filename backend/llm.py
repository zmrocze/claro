"""
LLM configuration and management for Carlo App
Uses Grok API with OpenAI-compatible interface
"""

import logging
from typing import Optional, List, Dict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import SecretStr

from backend.config import get_grok_api_key, GROK_API_BASE_URL, AppConfig

logger = logging.getLogger(__name__)


class LLMManager:
  """Manages LLM interactions using Grok via OpenAI-compatible API"""

  def __init__(
    self,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
  ):
    """
    Initialize LLM manager

    Args:
      api_key: Optional API key (will use config if not provided)
      model_name: Model name (defaults to config)
      temperature: Temperature for generation (defaults to config)
      max_tokens: Max tokens for generation (defaults to config)
    """
    self.api_key = api_key or get_grok_api_key()
    self.model_name = model_name or AppConfig.LLM_MODEL
    self.temperature = (
      temperature if temperature is not None else AppConfig.LLM_TEMPERATURE
    )
    self.max_tokens = max_tokens or AppConfig.LLM_MAX_TOKENS

    # Initialize the LLM client
    try:
      self.llm = ChatOpenAI(
        api_key=SecretStr(self.api_key),
        base_url=GROK_API_BASE_URL,
        model=self.model_name,
        temperature=self.temperature,
        max_completion_tokens=self.max_tokens,
        timeout=30.0,
        max_retries=3,
      )
      logger.info(f"LLM initialized with model: {self.model_name}")
    except Exception as e:
      logger.error(f"Failed to initialize LLM: {e}")
      raise

  def get_response(
    self,
    message: str,
    context: Optional[str] = None,
    system_prompt: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
  ) -> str:
    """
    Get a response from the LLM

    Args:
      message: User message
      context: Optional context from Zep memory
      system_prompt: Optional system prompt
      chat_history: Optional chat history

    Returns:
      LLM response as string
    """
    try:
      # Build the messages list
      messages = []

      # Add system prompt
      if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
      elif context:
        # If no system prompt but have context, create one
        system_content = f"""You are Carlo, a helpful AI assistant with access to personalized context about the user.

User Context:
{context}

Use this context to provide personalized and relevant responses."""
        messages.append(SystemMessage(content=system_content))
      else:
        # Default system prompt
        messages.append(
          SystemMessage(content="You are Carlo, a helpful and friendly AI assistant.")
        )

      # Add chat history if provided
      if chat_history:
        for msg in chat_history:
          if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
          elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

      # Add the current message
      messages.append(HumanMessage(content=message))

      # Get response from LLM
      response = self.llm.invoke(messages)

      return str(response.content)

    except Exception as e:
      logger.error(f"Error getting LLM response: {e}")
      raise

  async def get_response_async(
    self,
    message: str,
    context: Optional[str] = None,
    system_prompt: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
  ) -> str:
    """
    Get an async response from the LLM

    Args:
      message: User message
      context: Optional context from Zep memory
      system_prompt: Optional system prompt
      chat_history: Optional chat history

    Returns:
      LLM response as string
    """
    try:
      # Build the messages list
      messages = []

      # Add system prompt
      if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
      elif context:
        # If no system prompt but have context, create one
        system_content = f"""You are Carlo, a helpful AI assistant with access to personalized context about the user.

User Context:
{context}

Use this context to provide personalized and relevant responses."""
        messages.append(SystemMessage(content=system_content))
      else:
        # Default system prompt
        messages.append(
          SystemMessage(content="You are Carlo, a helpful and friendly AI assistant.")
        )

      # Add chat history if provided
      if chat_history:
        for msg in chat_history:
          if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
          elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

      # Add the current message
      messages.append(HumanMessage(content=message))

      # Get async response from LLM
      response = await self.llm.ainvoke(messages)

      return str(response.content)

    except Exception as e:
      logger.error(f"Error getting async LLM response: {e}")
      raise

  def create_prompt_template(
    self,
    system_template: str,
    include_context: bool = True,
    include_history: bool = True,
  ) -> ChatPromptTemplate:
    """
    Create a reusable prompt template

    Args:
      system_template: System message template
      include_context: Whether to include context placeholder
      include_history: Whether to include history placeholder

    Returns:
      ChatPromptTemplate object
    """
    messages: list = [("system", system_template)]

    if include_context:
      messages.append(("system", "User Context:\n{context}"))

    if include_history:
      messages.append(MessagesPlaceholder(variable_name="history"))

    messages.append(("human", "{input}"))

    return ChatPromptTemplate.from_messages(messages)  # type: ignore

  def get_streaming_response(
    self,
    message: str,
    context: Optional[str] = None,
    system_prompt: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
  ):
    """
    Get a streaming response from the LLM

    Args:
      message: User message
      context: Optional context from Zep memory
      system_prompt: Optional system prompt
      chat_history: Optional chat history

    Yields:
      Chunks of the LLM response
    """
    try:
      # Build the messages list
      messages = []

      # Add system prompt
      if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
      elif context:
        # If no system prompt but have context, create one
        system_content = f"""You are Carlo, a helpful AI assistant with access to personalized context about the user.

User Context:
{context}

Use this context to provide personalized and relevant responses."""
        messages.append(SystemMessage(content=system_content))
      else:
        # Default system prompt
        messages.append(
          SystemMessage(content="You are Carlo, a helpful and friendly AI assistant.")
        )

      # Add chat history if provided
      if chat_history:
        for msg in chat_history:
          if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
          elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

      # Add the current message
      messages.append(HumanMessage(content=message))

      # Stream response from LLM
      for chunk in self.llm.stream(messages):
        if chunk.content:
          yield chunk.content

    except Exception as e:
      logger.error(f"Error getting streaming LLM response: {e}")
      raise


# Singleton instance
_llm_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
  """
  Get or create the singleton LLM manager

  Returns:
    LLMManager instance
  """
  global _llm_manager

  if _llm_manager is None:
    _llm_manager = LLMManager()

  return _llm_manager


def test_llm_connection() -> bool:
  """
  Test the LLM connection with a simple query

  Returns:
    True if connection successful, False otherwise
  """
  try:
    llm = get_llm_manager()
    response = llm.get_response("Hello, please respond with 'Connection successful'")
    logger.info(f"LLM test response: {response}")
    return "successful" in response.lower()
  except Exception as e:
    logger.error(f"LLM connection test failed: {e}")
    return False
