"""
Tools for the LangGraph agent
Includes mock action tool and Zep search tools
"""

import logging
from langchain_core.tools import tool
from zep_cloud.client import AsyncZep
from backend.config import get_zep_api_key, AppConfig

logger = logging.getLogger(__name__)


def create_zep_tools(zep_client: AsyncZep, user_id: str):
  """
  Create Zep search tools configured for a specific user
  
  Args:
    zep_client: Async Zep client instance
    user_id: User ID to search for
    
  Returns:
    List of tools
  """
  
  @tool
  async def search_facts(query: str, limit: int = 5) -> list[str]:
    """
    Search for facts in all conversations had with a user.
    Use this when you need to recall specific information about the user's
    preferences, habits, history, or past conversations.
    
    Args:
      query: The search query
      limit: The number of results to return (defaults to 5)
      
    Returns:
      list: A list of facts that match the search query
    """
    try:
      result = await zep_client.graph.search(
        user_id=user_id, query=query, limit=limit, scope="edges"
      )
      facts = [edge.fact for edge in result.edges or []]
      if not facts:
        return ["No facts found for the query."]
      return facts
    except Exception as e:
      logger.error(f"Error searching facts: {e}")
      return [f"Error searching facts: {str(e)}"]
  
  @tool
  async def search_nodes(query: str, limit: int = 5) -> list[str]:
    """
    Search for entities/nodes in all conversations had with a user.
    Use this to find information about people, places, things, or concepts
    mentioned in past conversations.
    
    Args:
      query: The search query
      limit: The number of results to return (defaults to 5)
      
    Returns:
      list: A list of node summaries for nodes that match the search query
    """
    try:
      result = await zep_client.graph.search(
        user_id=user_id, query=query, limit=limit, scope="nodes"
      )
      summaries = [node.summary for node in result.nodes or []]
      if not summaries:
        return ["No nodes found for the query."]
      return summaries
    except Exception as e:
      logger.error(f"Error searching nodes: {e}")
      return [f"Error searching nodes: {str(e)}"]
  
  return [search_facts, search_nodes]


@tool
async def mock_action(description: str, parameters: dict) -> str:
  """
  A mock action tool for demonstration purposes.
  In production, this would be replaced with real actions.
  
  Args:
    description: Description of the action to perform
    parameters: Parameters for the action
    
  Returns:
    str: Result of the mock action
  """
  logger.info(f"Mock action called: {description} with params: {parameters}")
  return f"Mock action executed: {description}. This is a placeholder for real actions."

