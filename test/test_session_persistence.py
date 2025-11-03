#!/usr/bin/env python
"""Test script to verify session persistence implementation"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.sessions import SessionManager


def test_basic_persistence():
  """Test that messages are persisted to disk"""
  print("=" * 60)
  print("Test 1: Basic Message Persistence")
  print("=" * 60)

  with tempfile.TemporaryDirectory() as tmpdir:
    # Create manager with temporary storage
    with patch("backend.sessions.user_data_dir", return_value=tmpdir):
      manager = SessionManager()

      # Create a session
      session_id = manager.create_session()
      print(f"✓ Created session: {session_id}")
      print(f"✓ Using temp directory: {tmpdir}")

      # Add some messages
      manager.add_message("Hello, this is a test message", "user", session_id)
      manager.add_message("This is the assistant's response", "assistant", session_id)
      manager.add_message("Another user message", "user", session_id)
      print("✓ Added 3 messages to session")

      # Get storage directory
      session_dir = manager.storage_dir / session_id
      print(f"✓ Session directory: {session_dir}")

      # Wait a bit for async writes to complete
      print("  Waiting for async writes to complete...")
      time.sleep(0.5)

      # Check that files exist
      message_files = list(session_dir.glob("*.json"))
      print(f"✓ Found {len(message_files)} message files on disk")

      assert len(message_files) == 3, f"Expected 3 files, found {len(message_files)}"
      print("✓ All messages persisted successfully!")

      # Verify we can read messages from memory
      messages = manager.get_messages(session_id)
      print(f"✓ Retrieved {len(messages)} messages from memory cache")

      for i, msg in enumerate(messages, 1):
        print(f"  Message {i}: [{msg.role}] {msg.content[:50]}...")


def test_lazy_loading():
  """Test that sessions are restored from disk on app restart"""
  print("\n" + "=" * 60)
  print("Test 2: Session Restoration (App Restart Simulation)")
  print("=" * 60)

  with tempfile.TemporaryDirectory() as tmpdir:
    with patch("backend.sessions.user_data_dir", return_value=tmpdir):
      # Simulate first app run: create session and add messages
      manager1 = SessionManager()
      session_id = manager1.create_session()
      print(f"✓ [App Run 1] Created session: {session_id}")

      manager1.add_message("First message", "user", session_id)
      manager1.add_message("Second message", "assistant", session_id)
      manager1.add_message("Third message", "user", session_id)
      print("✓ [App Run 1] Added 3 messages")

      # Wait for async writes to complete
      time.sleep(0.5)
      print("✓ [App Run 1] Messages saved to disk")

      # Verify files exist on disk
      session_dir = manager1.storage_dir / session_id
      message_files = list(session_dir.glob("*.json"))
      assert len(message_files) == 3, (
        f"Expected 3 files on disk, found {len(message_files)}"
      )
      print(f"✓ [App Run 1] Verified {len(message_files)} files on disk")

      # Simulate app restart: create new manager (empty memory)
      manager2 = SessionManager()
      print("\n✓ [App Run 2] Simulated app restart - new SessionManager")

      # Session should NOT be in memory
      assert session_id not in manager2.sessions, (
        "Session should not be in memory after restart"
      )
      print("✓ [App Run 2] Confirmed session not in memory")

      # But directory should still exist on disk
      session_dir2 = manager2.storage_dir / session_id
      assert session_dir2.exists(), "Session directory should exist on disk"
      print("✓ [App Run 2] Session directory exists on disk")

      # This is the critical test: get_messages should restore from disk
      # This simulates frontend calling GET /api/chat/history/{session_id}
      messages = manager2.get_messages(session_id)
      print(f"✓ [App Run 2] get_messages() returned {len(messages)} messages")

      # Session should now be restored in memory
      assert session_id in manager2.sessions, (
        "Session should now be in memory after access"
      )
      print("✓ [App Run 2] Session restored to memory")

      # All messages should be loaded
      assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"
      print("✓ [App Run 2] All messages loaded successfully")

      # Verify message content
      assert messages[0].content == "First message"
      assert messages[1].content == "Second message"
      assert messages[2].content == "Third message"
      print("✓ [App Run 2] Message content verified")

      for i, msg in enumerate(messages, 1):
        print(f"  Message {i}: [{msg.role}] {msg.content}")


def test_cleanup():
  """Test message cleanup"""
  print("\n" + "=" * 60)
  print("Test 3: Cleanup")
  print("=" * 60)

  with tempfile.TemporaryDirectory() as tmpdir:
    with patch("backend.sessions.user_data_dir", return_value=tmpdir):
      manager = SessionManager()

      # Create multiple sessions with messages
      session_ids = []
      for i in range(3):
        session_id = manager.create_session()
        session_ids.append(session_id)
        manager.add_message(f"Message {i}", "user", session_id)
        print(f"✓ Created session {i + 1}: {session_id[:8]}...")

      # Wait for async writes
      time.sleep(0.5)

      # Get all sessions
      all_sessions = manager.get_all_sessions()
      print(f"✓ Found {len(all_sessions)} session(s)")
      assert len(all_sessions) == 3, f"Expected 3 sessions, found {len(all_sessions)}"

      # Verify files exist on disk
      sessions_dir = manager.storage_dir
      dirs_before = [d for d in sessions_dir.iterdir() if d.is_dir()]
      print(f"✓ Verified {len(dirs_before)} session directories on disk")

      # Delete all sessions (cleanup)
      for session_id in list(all_sessions.keys()):
        manager.delete_session(session_id)
        print(f"✓ Deleted session: {session_id[:8]}...")

      # Verify storage directory is cleaned
      remaining_dirs = [d for d in sessions_dir.iterdir() if d.is_dir()]

      assert len(remaining_dirs) == 0, (
        f"{len(remaining_dirs)} session directories still remain"
      )
      print("✓ All session directories cleaned up")


if __name__ == "__main__":
  print("\n🧪 Testing Session Persistence Implementation\n")

  tests = [
    ("Basic Persistence", test_basic_persistence),
    ("Lazy Loading", test_lazy_loading),
    ("Cleanup", test_cleanup),
  ]

  results = []

  for test_name, test_func in tests:
    try:
      test_func()
      results.append((test_name, True))
    except AssertionError as e:
      print(f"\n❌ Test '{test_name}' failed: {e}")
      results.append((test_name, False))
    except Exception as e:
      print(f"\n❌ Test '{test_name}' failed with exception: {e}")
      import traceback

      traceback.print_exc()
      results.append((test_name, False))

  # Print summary
  print("\n" + "=" * 60)
  print("Test Summary")
  print("=" * 60)

  for test_name, result in results:
    status = "✓ PASS" if result else "✗ FAIL"
    print(f"{status}: {test_name}")

  all_passed = all(result for _, result in results)

  if all_passed:
    print("\n✅ All tests passed!")
    sys.exit(0)
  else:
    print("\n❌ Some tests failed")
    sys.exit(1)
