# Agent Module

LangGraph agent implementation with Zep memory integration for Claro app.

## Structure

```
backend/agent/
├── __init__.py      # Module exports
├── agent.py         # Main LangGraph agent (CarloAgent)
├── state.py         # Agent state definition (AgentState)
├── tools.py         # Agent tools (Zep search, mock action)
└── README.md        # This file
```

## Quick Start

```python
from backend.agent import get_agent

# Get agent instance (singleton)
agent = await get_agent()

# Send a message
response = await agent.ainvoke(
    message="Hello! What can you help me with?",
    thread_id="conversation_thread_123"
)

print(response)
```

## Agent Features

### Zep Memory Integration

- Retrieves context from Zep on every message
- Saves all messages to Zep for knowledge graph building
- Maintains conversation continuity across sessions

### Available Tools

1. **search_facts**: Search for facts in user's conversation history
2. **search_nodes**: Search for entities/nodes in knowledge graph
3. **mock_action**: Placeholder for real actions (to be implemented)

### LangSmith Tracing

Enable tracing by setting environment variables:

```bash
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=Claro-Agent
```

## Architecture

### Agent Flow

```
Message → Get Context from Zep
       → Build Prompt with Context
       → LLM Processes (with tools)
       → Tool Execution (if needed)
       → Save to Zep
       → Return Response
```

### State Management

- **AgentState**: Holds messages, thread_id, user_id, names
- **LangGraph MemorySaver**: Maintains recent message history
- **Zep**: Long-term memory and knowledge graph

## Configuration

Required in `backend/config.py`:

- `GROK_API_KEY`: LLM API key
- `ZEP_API_KEY`: Zep API key (optional for local)
- `ZEP_USER_ID`: User identifier (auto-generated if not set)

Optional:

- `ZEP_USER_FIRST_NAME`, `ZEP_USER_LAST_NAME`
- `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`

## Development

### Adding New Tools

```python
from langchain_core.tools import tool

@tool
async def my_new_tool(param: str) -> str:
    """Tool description for the LLM"""
    # Your implementation
    return result

# Add to agent.py in __init__:
self.tools = [*zep_tools, mock_action, my_new_tool]
```

### Customizing System Prompt

Edit the `system_content` in `agent.py` chatbot function:

```python
system_content = f"""Your custom instructions...

User Context:
{memory.context}
"""
```

### Modifying Agent Behavior

The agent graph is built in `_build_graph()`:

- Modify the `chatbot` node for different processing
- Add more nodes for complex workflows
- Change conditional edges for different routing

## Testing

Run agent tests:

```bash
uv run python test/test_agent.py
```

Test specific functionality:

```python
async def test_my_feature():
    agent = await get_agent()
    response = await agent.ainvoke(
        message="test message",
        thread_id="test_thread"
    )
    assert "expected" in response
```

## Notes

- Agent is a singleton - one instance per app run
- Threads persist in Zep across app restarts
- Agent state is ephemeral (last 5 messages kept)
- Full history maintained in Zep
- Tools are user-specific for proper context
