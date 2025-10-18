"""
Test script for Carlo backend integration
Run with: uv run python test/test_backend.py
"""

import sys

# Test imports
print("Testing imports...")
try:
  from backend.sessions import get_session_manager
  from backend.agent import get_agent

  print("✓ All imports successful")
except ImportError as e:
  print(f"✗ Import error: {e}")
  sys.exit(1)


def test_session_manager():
  """Test session management"""
  print("\n=== Testing Session Manager ===")

  sessions = get_session_manager()

  # Create session
  session_id = sessions.create_session()
  print(f"✓ Created session: {session_id[:8]}...")

  # Add messages
  sessions.add_message("Hello, Carlo!", "user", session_id)
  sessions.add_message("Hello! How can I help you today?", "assistant", session_id)
  print("✓ Added messages to session")

  # Retrieve messages
  messages = sessions.get_messages(session_id)
  print(f"✓ Retrieved {len(messages)} messages")

  # Test thread ID
  thread_id = "test_thread_123"
  sessions.set_thread_id(session_id, thread_id)
  retrieved_thread = sessions.get_thread_id(session_id)
  assert retrieved_thread == thread_id
  print("✓ Thread ID management working")


async def test_agent():
  """Test LangGraph agent"""
  print("\n=== Testing Agent ===")

  try:
    agent = await get_agent()
    print(f"✓ Agent initialized for user: {agent.user_id}")
    print(f"✓ Using thread: {agent.thread_id[:8]}...")
    print(f"✓ Tools available: {len(agent.tools)}")
    return True

  except Exception as e:
    print(f"✗ Agent error: {e}")
    print("  Make sure GROK_API_KEY is set")
    return False


async def test_api_endpoints():
  """Test API endpoints"""
  print("\n=== Testing API Endpoints ===")

  try:
    import httpx

    # Check if server is running
    async with httpx.AsyncClient() as client:
      try:
        response = await client.get("http://localhost:8000/health")
        if response.status_code == 200:
          print("✓ Health endpoint working")
        else:
          print("⚠ Server not responding correctly")
          return False

        # Test chat endpoint
        response = await client.post(
          "http://localhost:8000/api/chat/message",
          json={"content": "Hello, this is a test"},
        )
        if response.status_code == 200:
          print("✓ Chat endpoint working")
        else:
          print(f"⚠ Chat endpoint returned {response.status_code}")

        # Test sessions endpoint
        response = await client.get("http://localhost:8000/api/chat/sessions")
        if response.status_code == 200:
          print("✓ Sessions endpoint working")
        else:
          print(f"⚠ Sessions endpoint returned {response.status_code}")

        # Test notifications config
        response = await client.get("http://localhost:8000/api/notifications/config")
        if response.status_code == 200:
          print("✓ Notifications endpoint working")
        else:
          print(f"⚠ Notifications endpoint returned {response.status_code}")

        # Test actions pending
        response = await client.get("http://localhost:8000/api/actions/pending")
        if response.status_code == 200:
          print("✓ Actions endpoint working")
        else:
          print(f"⚠ Actions endpoint returned {response.status_code}")

        return True

      except httpx.ConnectError:
        print("⚠ Could not connect to server at http://localhost:8000")
        print("  Make sure to run the server with: uv run python backend/main.py")
        return False

  except ImportError:
    print("⚠ httpx not installed, skipping API tests")
    print("  Install with: uv pip install httpx")
    return True
