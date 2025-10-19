"""
Custom exceptions for Carlo backend
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


class ErrorResponse(BaseModel):
  """Standardized error response model"""

  description: str = Field(..., description="Human-readable error message")
  name: str = Field(..., description="Unique error identifier")
  source: ErrorSource = Field(..., description="Where the error originated")
  caused_by: Optional[str] = Field(
    None, description="Original error details if this is a chained error"
  )


class CarloError(Exception):
  """
  Custom exception class for Carlo application errors.
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
    Initialize a Carlo error

    Args:
        description: Human-readable error message
        name: Unique error identifier (e.g., "RATE_LIMIT_EXCEEDED")
        source: Where the error originated from
        caused_by: Original error details if this wraps another error
    """
    self.description = description
    self.name = name
    self.source = source
    self.caused_by = caused_by
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
  ) -> "CarloError":
    """
    Create a CarloError from an existing exception

    Args:
        e: The original exception
        name: Error identifier for this error
        source: Where this error originated
        context: Additional context to prepend to the description

    Returns:
        CarloError with original exception details preserved
    """
    original_msg = str(e)
    description = f"{context}: {original_msg}" if context else original_msg

    return cls(
      description=description,
      name=name,
      source=source,
      caused_by=f"{e.__class__.__name__}: {original_msg}",
    )
