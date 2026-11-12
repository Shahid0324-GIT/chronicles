class DomainError(ValueError):
    """The requested graph violates the domain's rules."""


class NotFoundError(LookupError):
    """A requested atlas record does not exist."""
