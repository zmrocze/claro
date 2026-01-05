"""
Configuration module for Claro App
Handles secure API key storage and retrieval
"""

import os
import logging
from typing import Optional
import keyring
from dotenv import load_dotenv
import pynentry

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration constants
KEYRING_SERVICE = "claro-app"
GROK_API_KEY = "grok_api_key"
ZEP_API_KEY = "zep_api_key"

# API endpoints
GROK_API_BASE_URL = "https://api.x.ai/v1"  # Grok uses OpenAI-compatible API
ZEP_API_URL = os.getenv("ZEP_API_URL", None)  # Default to local Zep


def set_api_key(key_name: str, value: str) -> None:
  """
  Store an API key securely in the system keyring

  Args:
    key_name: Name of the key (e.g., 'grok_api_key')
    value: The API key value
  """
  try:
    keyring.set_password(KEYRING_SERVICE, key_name, value)
    logger.info(f"API key '{key_name}' stored successfully")
  except Exception as e:
    logger.error(f"Failed to store API key '{key_name}': {e}")
    raise


def get_api_key(key_name: str, env_fallback: Optional[str] = None) -> Optional[str]:
  """
  Retrieve an API key from keyring with optional environment variable fallback

  Args:
    key_name: Name of the key to retrieve
    env_fallback: Optional environment variable name to check if keyring fails

  Returns:
    The API key value or None if not found
  """
  # Try keyring first
  try:
    value = keyring.get_password(KEYRING_SERVICE, key_name)
    if value:
      logger.debug(f"API key '{key_name}' retrieved from keyring")
      return value
  except Exception as e:
    logger.warning(f"Failed to retrieve '{key_name}' from keyring: {e}")

  # Fall back to environment variable
  if env_fallback:
    value = os.getenv(env_fallback)
    if value:
      logger.debug(f"API key '{key_name}' retrieved from environment variable")
      return value

  # Fall back to pynentry prompt
  try:
    value = pynentry.get_pin(
      description=f"API key '{key_name}' not found in keyring or environment.\nPlease enter it below:",
      prompt=f"{key_name}:",
    )
    if value:
      logger.info(f"API key '{key_name}' entered via pynentry prompt")
      return value
  except pynentry.PinEntryCancelled:
    logger.warning(f"User cancelled pynentry prompt for '{key_name}'")
  except Exception as e:
    logger.warning(f"Failed to prompt for '{key_name}' using pynentry: {e}")

  logger.warning(
    f"API key '{key_name}' not found in keyring, environment, or user input"
  )
  return None


def get_grok_api_key() -> str:
  """Get Grok API key with validation"""
  key = get_api_key(GROK_API_KEY, "GROK_API_KEY")
  if not key:
    raise ValueError(
      "Grok API key not found. Please set it using 'set_api_key' or "
      "provide GROK_API_KEY environment variable"
    )
  return key


def get_zep_api_key() -> Optional[str]:
  """Get Zep API key (optional for local instances)"""
  return get_api_key(ZEP_API_KEY, "ZEP_API_KEY")


def check_required_keys() -> tuple[bool, list[str]]:
  """
  Check if all required API keys are present

  Returns:
    Tuple of (all_present: bool, missing_keys: list)
  """
  missing = []

  try:
    get_grok_api_key()
  except ValueError:
    missing.append("Grok API key")

  # Zep API key is optional for local instances
  if ZEP_API_URL != "http://localhost:8000" and not get_zep_api_key():
    missing.append("Zep API key (required for cloud instance)")

  return len(missing) == 0, missing


def initialize_config() -> None:
  """
  Initialize configuration and check for required keys
  Raises exception if required keys are missing
  """
  all_present, missing = check_required_keys()

  if not all_present:
    error_msg = f"Missing required API keys: {', '.join(missing)}"
    logger.error(error_msg)

    # Provide helpful instructions
    logger.info("\nTo set API keys, you can either:")
    logger.info("1. Set environment variables: GROK_API_KEY, ZEP_API_KEY")
    logger.info("2. Use the keyring (recommended for production):")
    logger.info(
      "   python -c \"from backend.config import set_api_key; set_api_key('grok_api_key', 'your-key-here')\""
    )

    raise ValueError(error_msg)

  logger.info("Configuration initialized successfully")


# Configuration class for other settings
class AppConfig:
  """Application configuration settings"""

  # Server settings
  HOST = os.getenv("HOST", "0.0.0.0")
  PORT = int(os.getenv("PORT", "8000"))

  # CORS settings
  CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:8000"
  ).split(",")

  # Session settings
  MAX_SESSION_MESSAGES = int(os.getenv("MAX_SESSION_MESSAGES", "500"))
  MAX_MESSAGE_AGE_HOURS = int(os.getenv("MAX_MESSAGE_AGE_HOURS", "3"))  # 30 days
  SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "72"))

  # LLM settings
  LLM_MODEL = os.getenv("LLM_MODEL", "grok-beta")
  LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "2.0"))
  LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4000"))
  LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")  # Options: "grok", "mock"

  # Memory provider settings
  MEMORY_PROVIDER = os.getenv("MEMORY_PROVIDER", "mock")  # Options: "zep", "mock"

  # Zep settings
  ZEP_API_URL = ZEP_API_URL

  # User settings
  ZEP_USER_ID = os.getenv("ZEP_USER_ID")  # None means will prompt or auto-generate
  ZEP_USER_FIRST_NAME = os.getenv("ZEP_USER_FIRST_NAME", "Claro")
  ZEP_USER_LAST_NAME = os.getenv("ZEP_USER_LAST_NAME", "User")
  ZEP_USER_EMAIL = os.getenv("ZEP_USER_EMAIL")

  # LangSmith settings (for tracing)
  LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
  LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "Claro-Agent")
  LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

  # Logging
  LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# Utility function for CLI key management
if __name__ == "__main__":
  import sys

  if len(sys.argv) < 2:
    print("Usage: python -m backend.config <command> [args]")
    print("Commands:")
    print("  check    - Check if all required keys are present")
    print("  set-grok <key> - Set Grok API key")
    print("  set-zep <key>  - Set Zep API key")
    sys.exit(1)

  command = sys.argv[1]

  if command == "check":
    all_present, missing = check_required_keys()
    if all_present:
      print("✓ All required API keys are present")
    else:
      print("✗ Missing keys:", ", ".join(missing))
      sys.exit(1)

  elif command == "set-grok" and len(sys.argv) == 3:
    set_api_key(GROK_API_KEY, sys.argv[2])
    print("✓ Grok API key set successfully")

  elif command == "set-zep" and len(sys.argv) == 3:
    set_api_key(ZEP_API_KEY, sys.argv[2])
    print("✓ Zep API key set successfully")

  else:
    print("Invalid command or arguments")
    sys.exit(1)
