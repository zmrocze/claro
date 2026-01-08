"""Memory provider module with factory for easy swapping between implementations"""

import logging
from typing import Optional

from .base import MemoryProvider
from .zep_memory import ZepMemory, get_memory_client
from .mock_memory import MockMemoryProvider
from backend.config import AppConfig, get_zep_api_key

logger = logging.getLogger(__name__)

__all__ = [
  "MemoryProvider",
  "ZepMemory",
  "MockMemoryProvider",
  "create_memory_provider",
  "get_memory_client",
]


def create_memory_provider(
  provider_type: Optional[str] = None,
  api_key: Optional[str] = None,
  api_url: Optional[str] = None,
) -> MemoryProvider:
  """
  Factory function to create memory provider based on configuration.
  This is the single place where ZEP_API_KEY is read and memory providers are initialized.

  Args:
    provider_type: Type of memory provider ("zep" or "mock"). Uses config if not provided.
    api_key: Optional API key for Zep. Reads from config if not provided.
    api_url: Optional API URL for Zep. Uses config if not provided.

  Returns:
    Initialized MemoryProvider instance

  Raises:
    ValueError: If provider_type is invalid
  """
  provider_type = provider_type or AppConfig.MEMORY_PROVIDER

  if provider_type == "mock":
    logger.info("Creating mock memory provider")
    return MockMemoryProvider()
  elif provider_type == "zep":
    logger.info("Creating Zep memory provider")
    # This is the ONLY place where we read ZEP_API_KEY
    zep_api_key = api_key or get_zep_api_key()
    zep_api_url = api_url or AppConfig.ZEP_API_URL
    logger.info(f"Using Zep API URL: {zep_api_url} and API Key: {zep_api_key[:8] if zep_api_key else "NONE"}...")
    return ZepMemory(api_key=zep_api_key, api_url=zep_api_url)
  else:
    raise ValueError(
      f"Invalid memory provider type: {provider_type}. Must be 'zep' or 'mock'"
    )
