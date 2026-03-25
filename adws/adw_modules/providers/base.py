"""Abstract base class for issue tracker providers (GitHub, GitLab, etc.)."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# --- Generic data models (provider-agnostic) ---

class IssueUser(BaseModel):
    """User model normalized across providers."""
    id: Optional[str] = None
    login: str  # GitHub: login, GitLab: username
    name: Optional[str] = None
    is_bot: bool = False


class IssueLabel(BaseModel):
    """Label model normalized across providers."""
    id: str
    name: str
    color: str = ""
    description: Optional[str] = None


class IssueMilestone(BaseModel):
    """Milestone model normalized across providers."""
    id: str
    number: Optional[int] = None
    title: str
    description: Optional[str] = None
    state: str = ""


class IssueComment(BaseModel):
    """Comment/note model normalized across providers."""
    id: str
    author: IssueUser
    body: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    class Config:
        populate_by_name = True


class Issue(BaseModel):
    """Issue model normalized across providers."""
    number: int  # GitHub: number, GitLab: iid
    title: str
    body: str  # GitHub: body, GitLab: description
    state: str
    author: IssueUser
    assignees: List[IssueUser] = []
    labels: List[IssueLabel] = []
    milestone: Optional[IssueMilestone] = None
    comments: List[IssueComment] = []
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    closed_at: Optional[datetime] = Field(None, alias="closedAt")
    url: str  # GitHub: url, GitLab: web_url

    class Config:
        populate_by_name = True


class IssueListItem(BaseModel):
    """Simplified issue model for list responses."""
    number: int
    title: str
    body: str
    labels: List[IssueLabel] = []
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        populate_by_name = True


class MergeRequestInfo(BaseModel):
    """Merge/Pull request info returned by provider operations."""
    number: Optional[str] = None
    url: Optional[str] = None
    mergeable: Optional[bool] = None
    state: Optional[str] = None


# --- Abstract provider interface ---

class IssueProvider(ABC):
    """Abstract interface for issue tracker operations.

    Implementations handle the CLI and API differences between
    GitHub (gh), GitLab (glab), etc.
    """

    # Bot identifier to prevent webhook loops
    BOT_IDENTIFIER = "[ADW-AGENTS]"

    @abstractmethod
    def get_repo_path(self) -> str:
        """Get the repository path (e.g., 'owner/repo') from git remote."""
        ...

    @abstractmethod
    def fetch_issue(self, issue_number: str, repo_path: str) -> Issue:
        """Fetch a single issue by number."""
        ...

    @abstractmethod
    def fetch_open_issues(self, repo_path: str) -> List[IssueListItem]:
        """Fetch all open issues."""
        ...

    @abstractmethod
    def fetch_issue_comments(self, repo_path: str, issue_number: int) -> List[Dict]:
        """Fetch raw comments for an issue (for cron trigger compatibility)."""
        ...

    @abstractmethod
    def make_issue_comment(self, issue_id: str, comment: str) -> None:
        """Post a comment on an issue."""
        ...

    @abstractmethod
    def mark_issue_in_progress(self, issue_id: str) -> None:
        """Mark an issue as in-progress (add label, assign)."""
        ...

    @abstractmethod
    def check_mr_exists(self, branch_name: str) -> Optional[str]:
        """Check if a merge/pull request exists for branch. Returns URL if found."""
        ...

    @abstractmethod
    def get_mr_number(self, branch_name: str) -> Optional[str]:
        """Get merge/pull request number for a branch."""
        ...

    @abstractmethod
    def approve_mr(self, mr_number: str) -> tuple[bool, Optional[str]]:
        """Approve a merge/pull request. Returns (success, error)."""
        ...

    @abstractmethod
    def merge_mr(self, mr_number: str, method: str = "squash") -> tuple[bool, Optional[str]]:
        """Merge a merge/pull request. Returns (success, error)."""
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name (e.g., 'github', 'gitlab')."""
        ...

    @abstractmethod
    def get_cli_name(self) -> str:
        """Return CLI tool name (e.g., 'gh', 'glab')."""
        ...

    @abstractmethod
    def get_mr_term(self) -> str:
        """Return the term for merge requests (e.g., 'PR', 'MR')."""
        ...

    def get_repo_url(self) -> str:
        """Get repository URL from git remote. Shared across providers."""
        import subprocess
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            raise ValueError(
                "No git remote 'origin' found. Please ensure you're in a git repository with a remote."
            )

    def find_keyword_from_comment(self, keyword: str, issue: Issue) -> Optional[IssueComment]:
        """Find the latest comment containing a keyword, skipping bot comments."""
        sorted_comments = sorted(issue.comments, key=lambda c: c.created_at, reverse=True)
        for comment in sorted_comments:
            if self.BOT_IDENTIFIER in comment.body:
                continue
            if keyword in comment.body:
                return comment
        return None
