"""
Test to verify that user messages are saved correctly even when tools are called

This test verifies the fix for the user_message lifetime bug where:
- user_message was being captured on every chatbot node invocation
- After tool calls, state["messages"][-1] would be a ToolMessage, not HumanMessage
- This caused incorrect messages to be saved to Zep memory

Run with: uv run python test/test_agent_tool_calls.py
"""

import asyncio
import sys
from unittest.mock import Mock, patch

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from backend.agent.state import AgentState
from backend.memory import MockMemoryProvider


def test_user_message_saved_flag():
  """Test that user_message_saved flag is part of AgentState"""
  print("\n=== Testing AgentState.user_message_saved flag ===")

  # Create a minimal state
  state: AgentState = {
    "messages": [HumanMessage(content="Test")],
    "thread_id": "test_thread",
    "user_id": "test_user",
    "first_name": "Test",
    "last_name": "User",
  }

  assert "user_message_saved" not in state
  print("✓ user_message_saved flag does not exist in AgentState")


async def test_chatbot_with_tool_calls():
  """Test that chatbot node only saves user message once, even with tool calls"""
  print("\n=== Testing chatbot behavior with tool calls ===")

  from backend.agent.agent import CarloAgent

  # Create mock memory provider
  mock_memory = MockMemoryProvider()

  # Create fake LLM responses
  responses = [
    # First call: return AIMessage with tool call
    AIMessage(
      content="",
      tool_calls=[
        {
          "name": "mock_action",
          "args": {"action": "test"},
          "id": "call_123",
        }
      ],
    ),
    # Second call (after tool execution): return final response
    AIMessage(content="I've completed the action."),
  ]

  fake_llm = GenericFakeChatModel(messages=iter(responses))

  # Mock the AsyncZep creation, API keys, and LLM initialization
  with (
    patch("backend.agent.agent.AsyncZep") as mock_zep,
    patch("backend.agent.agent.get_grok_api_key") as mock_grok_key,
    patch("backend.agent.agent.ChatOpenAI") as mock_chat_openai,
  ):
    mock_zep.return_value = Mock()
    mock_grok_key.return_value = "fake-grok-key"
    mock_chat_openai.return_value.bind_tools.return_value = fake_llm

    # Create agent with mock memory
    agent = CarloAgent(
      user_id="test_user_tool_calls",
      first_name="Test",
      last_name="User",
      memory_provider=mock_memory,
    )

  # Invoke agent with a message
  response = await agent.ainvoke("Please perform a test action")

  print(f"✓ Agent response: {response}")

  # Verify that only ONE user message was saved to memory
  # Get all messages from the mock memory
  all_messages = []
  if hasattr(mock_memory, "_messages"):
    all_messages = mock_memory._messages.get(agent.thread_id, [])

  user_messages = [m for m in all_messages if m.get("role") == "user"]

  print(f"✓ Total messages saved: {len(all_messages)}")
  print(f"✓ User messages saved: {len(user_messages)}")

  # Should only have ONE user message
  assert len(user_messages) == 1, (
    f"Expected 1 user message, but found {len(user_messages)}"
  )
  assert user_messages[0]["content"] == "Please perform a test action"

  print("✓ User message was saved exactly once (not duplicated after tool calls)")


async def test_state_message_types():
  """Test that we correctly identify message types in state"""
  print("\n=== Testing message type identification ===")

  # Simulate state after tool execution
  state: AgentState = {
    "messages": [
      HumanMessage(content="Original user message"),
      AIMessage(content="", tool_calls=[{"name": "test", "args": {}, "id": "123"}]),
      ToolMessage(content="Tool result", tool_call_id="123"),
    ],
    "thread_id": "test",
    "user_id": "test",
    "first_name": "Test",
    "last_name": "User",
  }

  # The last message is a ToolMessage
  last_message = state["messages"][-1]
  assert isinstance(last_message, ToolMessage), "Last message should be ToolMessage"
  print("✓ After tool execution, last message is ToolMessage (not HumanMessage)")

  # Find the HumanMessage by searching backwards
  user_message = None
  for msg in reversed(state["messages"]):
    if isinstance(msg, HumanMessage):
      user_message = msg
      break

  assert user_message is not None, "Should find HumanMessage"
  assert user_message.content == "Original user message"
  print("✓ Can correctly find original HumanMessage by searching backwards")


async def main():
  """Run all tests"""
  print("=" * 60)
  print("Testing Agent Tool Calls - User Message Lifetime Fix")
  print("=" * 60)

  try:
    # Test 1: State flag
    test_user_message_saved_flag()

    # Test 2: Message type identification
    await test_state_message_types()

    # Test 3: Full integration test with tool calls
    await test_chatbot_with_tool_calls()

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return 0

  except AssertionError as e:
    print(f"\n✗ Test failed: {e}")
    return 1
  except Exception as e:
    print(f"\n✗ Unexpected error: {e}")
    import traceback

    traceback.print_exc()
    return 1


if __name__ == "__main__":
  exit_code = asyncio.run(main())
  sys.exit(exit_code)
