from dataclasses import dataclass
import json
import asyncio
import logging
from zep_cloud.client import AsyncZep
from zep_cloud import Episode
from backend.config import get_api_key


def get_data(node):
  header_path = node.metadata.get("header_path", None)
  header_path = {"header_path": header_path} if header_path else {}
  file_path = {"file_path": node.metadata["file_path"]}
  text = {"text": node.text}
  return {**header_path, **file_path, **text}


@dataclass
class ZepConfig:
  api_key: str
  user_id: str

  @classmethod
  def get_zep_config(cls, args, logger):
    # Get api_key and user_id from command line args or config
    api_key = args.api_key if args.api_key else get_api_key("zep_api_key")
    user_id = args.user_id if args.user_id else get_api_key("zep_user_id")

    if not api_key:
      logger.error("Zep API key not found. Provide via --api-key or set in config.")
      raise ValueError("Zep API key not found")

    if not user_id:
      logger.error("Zep user ID not found. Provide via --user-id or set in config.")
      raise ValueError("Zep user ID not found")

    return ZepConfig(api_key=api_key, user_id=user_id)


async def add_all_to_zep(zep_config: ZepConfig, nodes) -> list[Episode]:
  zep = AsyncZep(api_key=zep_config.api_key)

  async with asyncio.TaskGroup() as tg:
    tasks = [
      tg.create_task(
        zep.graph.add(
          user_id=zep_config.user_id, data=json.dumps(get_data(node)), type="json"
        )
      )
      for node in nodes
    ]

  return [task.result() for task in tasks]


logger = logging.getLogger(__name__)


def zep_action(nodes, zep_config, printer):
  try:
    episodes = asyncio.run(add_all_to_zep(zep_config, nodes))
    printer(f"Successfully added {len(episodes)} episodes to Zep")

    # Print summary of first episode
    if episodes:
      episode = episodes[0]
      content_preview = episode.content[:200] + (
        "..." if len(episode.content) > 200 else ""
      )

      printer("\nFirst Episode Summary:")
      printer(f"  Score: {episode.score}")
      printer(f"  Source Description: {episode.source_description}")
      printer(f"  Content Preview:\n{content_preview}")
      printer("\n")
      printer("✓ Successfully added episodes to Zep")
      return episodes

  except Exception as e:
    logger.error(f"Failed to add episodes to Zep: {e}")
    raise e


def print_action(nodes):
  for node in nodes:
    print(node)
