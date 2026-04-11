"""Project-specific exception hierarchy."""

class Echo360Error(Exception):
    """Base exception for the package."""


class BrowserSetupError(Echo360Error):
    """Raised when Chrome or Selenium cannot be started."""


class AuthenticationRequired(Echo360Error):
    """Raised when Echo360 access still requires user authentication."""


class DiscoveryError(Echo360Error):
    """Raised when course or lesson metadata cannot be parsed."""


class MediaResolutionError(Echo360Error):
    """Raised when a lesson has no usable downloadable media source."""


class NativeCaptionError(Echo360Error):
    """Raised when native captions were requested but cannot be parsed."""


class DependencyMissingError(Echo360Error):
    """Raised when an optional runtime dependency is not installed."""


class TranscriptionError(Echo360Error):
    """Raised when transcription fails."""
