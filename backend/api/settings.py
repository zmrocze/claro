"""Settings and configuration endpoints"""

import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from platformdirs import user_config_dir

from backend.config import (
  GROK_API_KEY,
  KEYRING_SERVICE,
  ZEP_API_KEY,
  prompt_and_store_api_key,
)
from backend.exceptions import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ConfigInfo(BaseModel):
  config_path: str
  keyring_service: str


class ApiKeyRequest(BaseModel):
  provider: Literal["grok", "zep"]


class ApiKeyResponse(BaseModel):
  saved: bool
  message: str


def _config_path() -> Path:
  """Return the notification schedule config path (default location)."""
  return (
    Path(user_config_dir("claro", ensure_exists=True)) / "notification_schedule.yaml"
  )


@router.get("/config", response_model=ConfigInfo)
async def get_config_info() -> ConfigInfo:
  """Return basic configuration details for the app."""
  try:
    path = _config_path()
    return ConfigInfo(config_path=str(path), keyring_service=KEYRING_SERVICE)
  except AppError:
    raise
  except Exception as e:
    logger.error(f"Error loading config info: {e}")
    raise AppError.from_exception(
      e,
      name="SETTINGS_CONFIG_ERROR",
      source="backend",
      context="Failed to load settings configuration info",
    )


@router.post("/api-key", response_model=ApiKeyResponse)
async def set_api_key_via_prompt(request: ApiKeyRequest) -> ApiKeyResponse:
  """Prompt the user for an API key via pynentry and save it to keyring."""
  try:
    key_name = GROK_API_KEY if request.provider == "grok" else ZEP_API_KEY
    description = (
      f"Enter your {request.provider.title()} API key to store it securely in keyring."
    )

    value = prompt_and_store_api_key(
      key_name,
      description=description,
      prompt_label=f"{request.provider.upper()} API Key:",
    )

    if not value:
      raise AppError(
        description="API key entry was cancelled or empty",
        name="API_KEY_ENTRY_CANCELLED",
        source="backend",
      )

    return ApiKeyResponse(
      saved=True, message=f"{request.provider.title()} API key saved to keyring"
    )

  except AppError as e:
    # Re-raise structured application errors
    raise e
  except Exception as e:
    logger.exception("Failed to save API key via prompt")
    raise AppError.from_exception(
      e,
      name="SETTINGS_API_KEY_ERROR",
      source="backend",
      context="Failed to save API key via prompt",
    )
