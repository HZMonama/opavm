from __future__ import annotations

from dataclasses import dataclass


class OpavmError(Exception):
    """Base exception with user-facing remediation text."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def format(self) -> str:
        if self.hint:
            return f"{self.message} {self.hint}"
        return self.message


@dataclass
class ResolutionResult:
    version: str
    reason: str


class UnsupportedPlatformError(OpavmError):
    pass


class VersionNotConfiguredError(OpavmError):
    pass


class VersionNotInstalledError(OpavmError):
    pass


class DownloadError(OpavmError):
    pass


class GitHubLookupError(OpavmError):
    pass
