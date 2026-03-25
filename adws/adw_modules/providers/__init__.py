"""Provider abstraction for issue trackers (GitHub, GitLab).

Usage:
    from adw_modules.providers import get_provider
    provider = get_provider()
    issue = provider.fetch_issue("123", provider.get_repo_path())

Provider selection (in priority order):
    1. ADW_PROVIDER env var: "github" or "gitlab"
    2. Auto-detect from git remote URL
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


def _detect_provider_from_remote() -> str:
    """Auto-detect provider by examining git remotes.

    Priority:
    1. If ADW_GIT_REMOTE is set, use that remote name
    2. If 'gitlab' remote exists, use gitlab
    3. If 'origin' contains 'gitlab', use gitlab
    4. Default to github
    """
    remote_name = os.getenv("ADW_GIT_REMOTE")

    if remote_name:
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
            pass

    # Check if 'gitlab' remote exists
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "gitlab"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return "gitlab"
    except Exception:
        pass

    # Check origin URL
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and "gitlab" in result.stdout.lower():
            return "gitlab"
    except Exception:
        pass

    return "github"


def get_provider(force: Optional[str] = None) -> IssueProvider:
    """Get the active issue provider (singleton).

    Args:
        force: Override provider selection ("github" or "gitlab").
               If None, uses ADW_PROVIDER env var or auto-detection.

    Returns:
        The active IssueProvider instance.
    """
    global _provider

    provider_name = force or os.getenv("ADW_PROVIDER") or _detect_provider_from_remote()

    # Return cached if same provider
    if _provider is not None and _provider.get_provider_name() == provider_name:
        return _provider

    if provider_name == "gitlab":
        from .gitlab_provider import GitLabProvider
        remote_name = os.getenv("ADW_GIT_REMOTE", "gitlab")
        _provider = GitLabProvider(remote_name=remote_name)
    elif provider_name == "github":
        from .github_provider import GitHubProvider
        _provider = GitHubProvider()
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
