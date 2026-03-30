#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv", "pydantic"]
# ///

"""
Issue Tracker Facade - AI Developer Workflow (ADW)

Thin facade that delegates to the active provider (GitHub or GitLab).
All existing imports continue to work unchanged:

    from adw_modules.github import fetch_issue, make_issue_comment, ...

Provider is selected via:
    - ADW_GIT_REMOTE_NAME env var (default: "origin") — provider auto-detected from URL
"""

from typing import Dict, List, Optional

from .providers import get_provider
from .providers.base import Issue, IssueComment, IssueListItem

# Re-export the bot identifier (used by many modules)
ADW_BOT_IDENTIFIER = "[ADW-AGENTS]"

# --- Legacy Pydantic type aliases for backward compatibility ---
# These map the old GitHub* types to the new provider-agnostic types.
# Existing code like `issue: GitHubIssue = fetch_issue(...)` continues to work.
from .providers.base import Issue as GitHubIssue
from .providers.base import IssueComment as GitHubComment
from .providers.base import IssueListItem as GitHubIssueListItem
from .providers.base import IssueUser as GitHubUser
from .providers.base import IssueLabel as GitHubLabel
from .providers.base import IssueMilestone as GitHubMilestone


def get_github_env() -> Optional[dict]:
    """Legacy helper. Provider handles auth internally.
    Returns None (inherit parent env) for backward compat with subprocess calls."""
    return None


def get_repo_url() -> str:
    """Get repository URL from git remote."""
    return get_provider().get_repo_url()


def extract_repo_path(url: str) -> str:
    """Extract owner/repo from URL. Delegates to provider."""
    return get_provider().get_repo_path()


def fetch_issue(issue_number: str, repo_path: str) -> Issue:
    """Fetch issue using the active provider CLI."""
    return get_provider().fetch_issue(issue_number, repo_path)


def make_issue_comment(issue_id: str, comment: str) -> None:
    """Post a comment to an issue."""
    get_provider().make_issue_comment(issue_id, comment)


def mark_issue_in_progress(issue_id: str) -> None:
    """Mark issue as in progress."""
    get_provider().mark_issue_in_progress(issue_id)


def fetch_open_issues(repo_path: str) -> List[IssueListItem]:
    """Fetch all open issues."""
    return get_provider().fetch_open_issues(repo_path)


def fetch_issue_comments(repo_path: str, issue_number: int) -> List[Dict]:
    """Fetch all comments for a specific issue."""
    return get_provider().fetch_issue_comments(repo_path, issue_number)


def find_keyword_from_comment(keyword: str, issue: Issue) -> Optional[IssueComment]:
    """Find the latest comment containing a specific keyword."""
    return get_provider().find_keyword_from_comment(keyword, issue)
