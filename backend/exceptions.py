"""
Custom exceptions for Claro backend
"""

from typing import Literal, Optional, cast
from pydantic import BaseModel, Field


# All possible error sources in the application
ErrorSource = Literal[
  "rate_limiter",  # Rate limiting middleware
  "validation",  # Request validation errors
  "agent",  # LangGraph agent errors
  "backend",  # General backend API/business logic errors
  "actions",  # Action execution/confirmation subsystem
  "notifications",  # Notification scheduling/management subsystem
  "network",  # Network/connection errors
  "http",  # HTTP protocol errors
  "unknown",  # Uncategorized errors
]


def get_status_code(source: ErrorSource) -> int:
  """Determine HTTP status code based on error source"""
  if source == "rate_limiter":
    return 429  # Too Many Requests
  elif source == "validation":
    return 400  # Bad Request
  elif source in [
    "http",
    "agent",
    "backend",
    "actions",
    "notifications",
    "unknown",
    "network",
  ]:
    return 500  # Internal Server Error
  else:
    # This should never be reached if all ErrorSource cases are covered
    return 500


class ErrorResponse(BaseModel):
  """Standardized error response model"""

  description: str = Field(..., description="Human-readable error message")
  name: str = Field(..., description="Unique error identifier")
  source: ErrorSource = Field(..., description="Where the error originated")
  caused_by: Optional[str] = Field(
    None, description="Original error details if this is a chained error"
  )


class AppError(Exception):
  """
  Custom exception class for Claro application errors.
  All errors should be converted to this format for consistent handling.
  """

  def __init__(
    self,
    description: str,
    name: str,
    source: ErrorSource,
    caused_by: Optional[str] = None,
  ):
    """
    Initialize a Claro error

    Args:
        description: Human-readable error message
        name: Unique error identifier (e.g., "RATE_LIMIT_EXCEEDED")
        source: Where the error originated from
        caused_by: Original error details if this wraps another error
    """
    self.description: str = description
    self.name: str = name
    self.source: ErrorSource = source
    self.caused_by: Optional[str] = caused_by
    super().__init__(description)

  def to_response(self) -> ErrorResponse:
    """Convert to ErrorResponse model for API responses"""
    return ErrorResponse(
      description=self.description,
      name=self.name,
      source=cast(ErrorSource, self.source),
      caused_by=self.caused_by,
    )

  @classmethod
  def from_exception(
    cls,
    e: Exception,
    name: str,
    source: ErrorSource,
    context: Optional[str] = None,
  ) -> "AppError":
    """
    Create a AppError from an existing exception

    Args:
        e: The original exception
        name: Error identifier for this error
        source: Where this error originated
        context: Additional context to prepend to the description

    Returns:
        AppError with original exception details preserved
    """
    original_msg = str(e)
    description = f"{context}: {original_msg}" if context else original_msg

    return cls(
      description=description,
      name=name,
      source=source,
      caused_by=f"{e.__class__.__name__}: {original_msg}",
    )
