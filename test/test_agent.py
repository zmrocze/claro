"""
Test script for LangGraph agent with Zep integration
Run with: uv run pytest test/test_agent.py
"""

import asyncio
import logging
import sys

from backend.agent import get_agent
from backend.config import check_required_keys, AppConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_agent_creation():
  """Test agent initialization"""
  logger.info("=== Testing Agent Creation ===")

  try:
    # Check API keys
    all_present, missing = check_required_keys()
    if not all_present:
      logger.warning(f"Missing API keys: {missing}")
      logger.info("Skipping agent test due to missing keys")
      return False

    # Create agent
    agent = await get_agent()
    logger.info(f"✓ Agent created for user: {agent.user_id}")
    logger.info(f"✓ User: {agent.first_name} {agent.last_name}")
    logger.info(f"✓ Tools available: {len(agent.tools)}")

    for tool in agent.tools:
      logger.info(f"  - {tool.name}: {tool.description}")

    return True

  except Exception as e:
    logger.error(f"✗ Agent creation failed: {e}", exc_info=True)
    return False


async def test_agent_invoke():
  """Test agent invocation with a simple message"""
  logger.info("\n=== Testing Agent Invocation ===")

  try:
    agent = await get_agent()

    # Agent uses single thread per user
    logger.info(f"✓ Using agent thread: {agent.thread_id}")

    # Test simple message
    logger.info("Sending test message...")
    response = await agent.ainvoke(
      message="Hello! Can you introduce yourself?",
    )

    logger.info("✓ Agent response received:")
    logger.info(f"  {response[:200]}...")

    return True

  except Exception as e:
    logger.error(f"✗ Agent invocation failed: {e}", exc_info=True)
    return False


async def test_agent_with_tools():
  """Test agent with tool usage (mock action)"""
  logger.info("\n=== Testing Agent with Tools ===")

  try:
    agent = await get_agent()

    # Uses single thread per user
    logger.info(f"✓ Using agent thread: {agent.thread_id}")

    # Test tool usage
    logger.info("Asking agent to use a tool...")
    response = await agent.ainvoke(
      message="Please perform a mock action to test something with parameter 'test_value'",
    )

    logger.info("✓ Tool usage response:")
    logger.info(f"  {response[:200]}...")

    return True

  except Exception as e:
    logger.error(f"✗ Tool usage test failed: {e}", exc_info=True)
    return False


def test_configuration():
  """Test configuration values"""
  logger.info("\n=== Testing Configuration ===")
  logger.info(f"✓ LLM Model: {AppConfig.LLM_MODEL}")
  logger.info(f"✓ LLM Temperature: {AppConfig.LLM_TEMPERATURE}")
  logger.info(f"✓ Zep API URL: {AppConfig.ZEP_API_URL}")
  logger.info(f"✓ User First Name: {AppConfig.ZEP_USER_FIRST_NAME}")
  logger.info(f"✓ User Last Name: {AppConfig.ZEP_USER_LAST_NAME}")
  logger.info(f"✓ LangSmith Tracing: {AppConfig.LANGCHAIN_TRACING_V2}")

  if AppConfig.LANGCHAIN_TRACING_V2:
    logger.info(f"✓ LangSmith Project: {AppConfig.LANGSMITH_PROJECT}")


async def run_all_tests():
  """Run all tests"""
  logger.info("=== Starting Agent Tests ===\n")

  results = {
    "configuration": test_configuration(),
    "agent_creation": await test_agent_creation(),
    "agent_invoke": await test_agent_invoke(),
    "agent_tools": await test_agent_with_tools(),
  }

  logger.info("\n=== Test Results ===")
  for test_name, result in results.items():
    status = "✓ PASSED" if result else "✗ FAILED"
    logger.info(f"{status}: {test_name}")

  passed = sum(results.values())
  total = len(results)
  logger.info(f"\nTotal: {passed}/{total} tests passed")

  return all(results.values())


if __name__ == "__main__":
  success = asyncio.run(run_all_tests())
  sys.exit(0 if success else 1)
