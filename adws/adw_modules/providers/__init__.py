"""Provider abstraction for issue trackers (GitHub, GitLab).

Usage:
    from adw_modules.providers import get_provider
    provider = get_provider()
    issue = provider.fetch_issue("123", provider.get_repo_path())

Environment variables:
    ADW_GIT_REMOTE_NAME: Git remote name to push/pull from (default: "origin").
                         Provider type (GitHub vs GitLab) is auto-detected from the remote URL.
"""

import os
import subprocess
from typing import Optional

from .base import (
    IssueProvider,
    Issue,
    IssueComment,
    IssueLabel,
    IssueListItem,
    IssueMilestone,
    IssueUser,
    MergeRequestInfo,
)

# Singleton provider instance
_provider: Optional[IssueProvider] = None


def _get_remote_name() -> str:
    """Return the configured git remote name (default: "origin")."""
    return os.getenv("ADW_GIT_REMOTE_NAME", "origin")


def _detect_provider_from_remote(remote_name: str) -> str:
    """Auto-detect provider type by examining the git remote URL.

    Returns "gitlab" if the URL contains "gitlab", otherwise "github".
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", remote_name],
            capture_output=True, text=True, check=True,
        )
        url = result.stdout.strip().lower()
        if "gitlab" in url:
            return "gitlab"
        return "github"
    except subprocess.CalledProcessError:
        return "github"


def get_provider(force: Optional[str] = None) -> IssueProvider:
    """Get the active issue provider (singleton).

    Provider type is auto-detected from the ADW_GIT_REMOTE_NAME remote URL.
    Use the ``force`` parameter only in tests or internal overrides.

    Args:
        force: Override provider selection ("github" or "gitlab").

    Returns:
        The active IssueProvider instance.
    """
    global _provider

    remote_name = _get_remote_name()
    provider_name = force or _detect_provider_from_remote(remote_name)

    # Return cached if same provider
    if _provider is not None and _provider.get_provider_name() == provider_name:
        return _provider

    if provider_name == "gitlab":
        from .gitlab_provider import GitLabProvider
        _provider = GitLabProvider(remote_name=remote_name)
    elif provider_name == "github":
        from .github_provider import GitHubProvider
        _provider = GitHubProvider(remote_name=remote_name)
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use 'github' or 'gitlab'.")

    return _provider


def reset_provider() -> None:
    """Reset the singleton provider (useful for testing)."""
    global _provider
    _provider = None


__all__ = [
    "get_provider",
    "reset_provider",
    "IssueProvider",
    "Issue",
    "IssueComment",
    "IssueLabel",
    "IssueListItem",
    "IssueMilestone",
    "IssueUser",
    "MergeRequestInfo",
]
