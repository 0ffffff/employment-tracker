"""User-facing CLI errors (exit code 1 in main)."""


class TrackError(Exception):
    pass


class ValidationError(TrackError):
    pass


class NotFoundError(TrackError):
    pass


class NonInteractiveError(TrackError):
    pass


class CancelledError(TrackError):
    pass
