"""Domain-level exceptions mapped to HTTP responses by FastAPI handlers."""


class AppError(Exception):
  """Base class for domain errors."""


class NotFound(AppError):
  """Raised when an entity does not exist."""


class ValidationError(AppError):
  """Raised when a business rule is violated."""
