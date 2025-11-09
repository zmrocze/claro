from dataclasses import dataclass
import json
import asyncio
from zep_cloud.client import AsyncZep
from zep_cloud import Episode


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
