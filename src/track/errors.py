class TrackError(Exception):
    """Base class for expected CLI errors."""


class ValidationError(TrackError):
    """Raised when user input is invalid."""


class NotFoundError(TrackError):
    """Raised when required data cannot be found."""


class NonInteractiveError(TrackError):
    """Raised when interactive flow is required but unavailable."""


class CancelledError(TrackError):
    """Raised when user cancels an operation."""
