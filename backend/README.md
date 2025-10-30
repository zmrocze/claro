# Claro Backend

FastAPI-based backend for the Claro personal AI assistant app.

## Quick Start

### 1. Environment Setup

Copy the development environment file and configure it:

```bash
cp .env.dev .env
```

Edit `.env` and set at minimum:

- `GROK_API_KEY` - Your Grok API key (required)
- `ZEP_API_KEY` - Your Zep API key (if using cloud Zep)

### 2. Memory Provider Configuration

The backend supports two memory providers:

#### Option A: Zep (Production)

```bash
# .env
MEMORY_PROVIDER=zep
ZEP_API_URL=http://localhost:8000  # or cloud URL
ZEP_API_KEY=your_key_here  # optional for local
```

#### Option B: Mock (Testing/Development)

```bash
# .env
MEMORY_PROVIDER=mock
```

The mock provider stores everything in memory - perfect for testing without Zep
infrastructure.

### 3. Run the Server

```bash
# From project root
uv run python -m backend.main
```

## Architecture

### Memory Provider System

The memory layer uses a clean factory pattern for easy swapping:

```python
from backend.memory import create_memory_provider
from backend.agent import new_agent

# Create memory provider (reads from config)
memory = create_memory_provider()

# Or specify explicitly
memory = create_memory_provider(provider_type="mock")

# Create agent with memory provider
agent = new_agent(user_id="test_user", memory_provider=memory)
```

**Key Design Principles:**

- Single source of truth: `create_memory_provider()` is the only place where
  `ZEP_API_KEY` is read
- Dependency injection: Agent receives initialized memory provider
- Easy testing: Use `MEMORY_PROVIDER=mock` for tests

### Project Structure

```
backend/
├── agent/              # LangGraph agent implementation
│   ├── agent.py       # CarloAgent class
│   ├── state.py       # Agent state definition
│   └── tools.py       # Agent tools
├── api/               # FastAPI endpoints
│   ├── chat.py        # Chat endpoints
│   ├── actions.py     # Action endpoints
│   └── notifications.py
├── memory/            # Memory provider abstraction
│   ├── base.py        # MemoryProvider interface
│   ├── zep_memory.py  # Zep implementation
│   ├── mock_memory.py # Mock implementation
│   └── __init__.py    # Factory function
├── config.py          # Configuration management
├── main.py           # FastAPI application
└── sessions.py       # Session management
```

## Configuration

All configuration is managed through environment variables. See `.env.dev` for
available options.

### API Keys

Store API keys securely using the system keyring (recommended for production):

```python
from backend.config import set_api_key

set_api_key("grok_api_key", "your-key-here")
set_api_key("zep_api_key", "your-key-here")
```

Or use environment variables (easier for development):

```bash
export GROK_API_KEY=your-key-here
export ZEP_API_KEY=your-key-here
```

### LangSmith Tracing (Optional)

Enable LangSmith for debugging and monitoring:

```bash
# .env
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=Claro-Agent
```

## Testing

Run tests with:

```bash
uv run python test/test_agent_tool_calls.py
```

Tests automatically use the mock memory provider.

## Development

### Using Mock Memory

For development without Zep:

```bash
# .env
MEMORY_PROVIDER=mock
```

This allows you to develop and test the entire application without running Zep.

### Creating a New Agent

```python
from backend.agent import new_agent

# Uses config to determine memory provider
agent = new_agent(user_id="my_user")

# Or provide specific memory provider
from backend.memory import MockMemoryProvider

memory = MockMemoryProvider()
agent = new_agent(user_id="my_user", memory_provider=memory)
```

## API Endpoints

- `POST /api/chat/message` - Send a message to the agent
- `GET /api/chat/history/{session_id}` - Get conversation history
- `POST /api/chat/session` - Create a new session
- `DELETE /api/chat/history/{session_id}` - Clear conversation history

See the API documentation at `http://localhost:8000/docs` when the server is
running.
