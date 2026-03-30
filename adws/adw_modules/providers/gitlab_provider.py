"""GitLab provider implementation using the glab CLI."""

import json
import os
import subprocess
import sys
from typing import Dict, List, Optional

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


class GitLabProvider(IssueProvider):
    """GitLab implementation of the issue provider interface."""

    def __init__(self, remote_name: str = "origin"):
        super().__init__(remote_name=remote_name)

    def get_provider_name(self) -> str:
        return "gitlab"

    def get_cli_name(self) -> str:
        return "glab"

    def get_mr_term(self) -> str:
        return "MR"

    def get_repo_path(self) -> str:
        """Extract group/project from GitLab URL.

        Handles:
          https://gitlab.croz.net/pzrinscak/tac-7.git -> pzrinscak/tac-7
          https://gitlab.croz.net/group/sub/project.git -> group/sub/project
        """
        url = self.get_repo_url()
        # Strip protocol + hostname
        # e.g. https://gitlab.croz.net/pzrinscak/tac-7.git
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")
        if path.endswith(".git"):
            path = path[:-4]
        return path

    def _get_hostname(self) -> str:
        """Extract hostname from the remote URL."""
        from urllib.parse import urlparse
        url = self.get_repo_url()
        return urlparse(url).hostname or "gitlab.com"

    def _parse_user(self, data: dict) -> IssueUser:
        return IssueUser(
            id=str(data.get("id", "")),
            login=data.get("username", ""),
            name=data.get("name"),
            is_bot=data.get("bot", False),
        )

    def _parse_label(self, name: str) -> IssueLabel:
        """GitLab issue list returns labels as plain strings."""
        return IssueLabel(id=name, name=name)

    def _parse_label_detail(self, data: dict) -> IssueLabel:
        """Parse label from label_details (full object)."""
        return IssueLabel(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            color=data.get("color", ""),
            description=data.get("description"),
        )

    def _fetch_notes(self, repo_path: str, issue_number: int) -> List[IssueComment]:
        """Fetch issue notes (comments) via glab API."""
        encoded_path = repo_path.replace("/", "%2F")
        try:
            result = subprocess.run(
                ["glab", "api", f"projects/{encoded_path}/issues/{issue_number}/notes",
                 "--hostname", self._get_hostname()],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                print(f"Warning: Could not fetch notes for issue #{issue_number}: {result.stderr}", file=sys.stderr)
                return []
            notes_data = json.loads(result.stdout)
            comments = []
            for n in notes_data:
                # Skip system notes (label changes, assignments, etc.)
                if n.get("system", False):
                    continue
                comments.append(IssueComment(
                    id=str(n["id"]),
                    author=self._parse_user(n.get("author", {})),
                    body=n.get("body", ""),
                    createdAt=n.get("created_at", ""),
                    updatedAt=n.get("updated_at"),
                ))
            # Sort oldest first
            comments.sort(key=lambda c: c.created_at)
            return comments
        except Exception as e:
            print(f"Warning: Error fetching notes: {e}", file=sys.stderr)
            return []

    def fetch_issue(self, issue_number: str, repo_path: str) -> Issue:
        cmd = [
            "glab", "issue", "view", str(issue_number),
            "-R", repo_path, "--output", "json",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(result.stderr, file=sys.stderr)
                sys.exit(result.returncode)

            data = json.loads(result.stdout)

            # Parse labels - GitLab returns labels as string array
            labels = []
            if data.get("label_details"):
                labels = [self._parse_label_detail(l) for l in data["label_details"]]
            elif data.get("labels"):
                labels = [self._parse_label(name) for name in data["labels"]]

            # Parse milestone
            milestone = None
            if data.get("milestone"):
                m = data["milestone"]
                milestone = IssueMilestone(
                    id=str(m.get("id", "")),
                    number=m.get("iid"),
                    title=m.get("title", ""),
                    description=m.get("description"),
                    state=m.get("state", ""),
                )

            # Fetch comments separately (GitLab doesn't include them in issue view)
            comments = self._fetch_notes(repo_path, int(issue_number))

            return Issue(
                number=data["iid"],
                title=data["title"],
                body=data.get("description", "") or "",
                state=data.get("state", ""),
                author=self._parse_user(data.get("author", {})),
                assignees=[self._parse_user(a) for a in data.get("assignees", [])],
                labels=labels,
                milestone=milestone,
                comments=comments,
                createdAt=data.get("created_at", ""),
                updatedAt=data.get("updated_at", ""),
                closedAt=data.get("closed_at"),
                url=data.get("web_url", ""),
            )
        except FileNotFoundError:
            print("Error: GitLab CLI (glab) is not installed.", file=sys.stderr)
            print("\nTo install glab:", file=sys.stderr)
            print("  - macOS: brew install glab", file=sys.stderr)
            print("  - Linux: See https://gitlab.com/gitlab-org/cli#installation", file=sys.stderr)
            print("\nAfter installation, authenticate with: glab auth login", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error parsing issue data: {e}", file=sys.stderr)
            sys.exit(1)

    def fetch_open_issues(self, repo_path: str) -> List[IssueListItem]:
        try:
            cmd = [
                "glab", "issue", "list", "-R", repo_path,
                "--per-page", "100", "--output", "json",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            issues_data = json.loads(result.stdout)
            issues = []
            for d in issues_data:
                labels = []
                if d.get("label_details"):
                    labels = [self._parse_label_detail(l) for l in d["label_details"]]
                elif d.get("labels"):
                    labels = [self._parse_label(name) for name in d["labels"]]

                issues.append(IssueListItem(
                    number=d["iid"],
                    title=d["title"],
                    body=d.get("description", "") or "",
                    labels=labels,
                    createdAt=d.get("created_at", ""),
                    updatedAt=d.get("updated_at", ""),
                ))
            print(f"Fetched {len(issues)} open issues")
            return issues
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to fetch issues: {e.stderr}", file=sys.stderr)
            return []
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse issues JSON: {e}", file=sys.stderr)
            return []

    def fetch_issue_comments(self, repo_path: str, issue_number: int) -> List[Dict]:
        """Fetch raw comments for cron trigger compatibility."""
        encoded_path = repo_path.replace("/", "%2F")
        try:
            result = subprocess.run(
                ["glab", "api", f"projects/{encoded_path}/issues/{issue_number}/notes",
                 "--hostname", self._get_hostname()],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                print(f"ERROR: Failed to fetch comments for issue #{issue_number}: {result.stderr}", file=sys.stderr)
                return []
            notes = json.loads(result.stdout)
            # Filter out system notes, normalize field names for cron trigger
            comments = []
            for n in notes:
                if n.get("system", False):
                    continue
                comments.append({
                    "id": n.get("id"),
                    "body": n.get("body", ""),
                    "createdAt": n.get("created_at", ""),
                    "author": {
                        "login": n.get("author", {}).get("username", ""),
                    },
                })
            comments.sort(key=lambda c: c.get("createdAt", ""))
            return comments
        except Exception as e:
            print(f"ERROR: Failed to fetch comments for issue #{issue_number}: {e}", file=sys.stderr)
            return []

    def make_issue_comment(self, issue_id: str, comment: str) -> None:
        repo_path = self.get_repo_path()
        if not comment.startswith(self.BOT_IDENTIFIER):
            comment = f"{self.BOT_IDENTIFIER} {comment}"

        cmd = ["glab", "issue", "note", str(issue_id), "-R", repo_path, "--message", comment]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Successfully posted comment to issue #{issue_id}")
            else:
                print(f"Error posting comment: {result.stderr}", file=sys.stderr)
                raise RuntimeError(f"Failed to post comment: {result.stderr}")
        except Exception as e:
            print(f"Error posting comment: {e}", file=sys.stderr)
            raise

    def mark_issue_in_progress(self, issue_id: str) -> None:
        repo_path = self.get_repo_path()

        # Add label
        cmd = ["glab", "issue", "update", str(issue_id), "-R", repo_path, "--label", "in_progress"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Note: Could not add 'in_progress' label: {result.stderr}")

        # Assign to self - use glab API
        encoded_path = repo_path.replace("/", "%2F")
        hostname = self._get_hostname()
        # Get current user
        user_result = subprocess.run(
            ["glab", "api", "user", "--hostname", hostname],
            capture_output=True, text=True,
        )
        if user_result.returncode == 0:
            user_data = json.loads(user_result.stdout)
            user_id = user_data.get("id")
            if user_id:
                subprocess.run(
                    ["glab", "api", "-X", "PUT",
                     f"projects/{encoded_path}/issues/{issue_id}",
                     "-f", f"assignee_ids[]={user_id}",
                     "--hostname", hostname],
                    capture_output=True, text=True,
                )
                print(f"Assigned issue #{issue_id} to self")

    def check_mr_exists(self, branch_name: str) -> Optional[str]:
        try:
            repo_path = self.get_repo_path()
        except Exception:
            return None
        result = subprocess.run(
            ["glab", "mr", "list", "-R", repo_path,
             "--source-branch", branch_name, "--output", "json"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            mrs = json.loads(result.stdout)
            if mrs:
                return mrs[0].get("web_url")
        return None

    def get_mr_number(self, branch_name: str) -> Optional[str]:
        try:
            repo_path = self.get_repo_path()
        except Exception:
            return None
        result = subprocess.run(
            ["glab", "mr", "list", "-R", repo_path,
             "--source-branch", branch_name, "--output", "json"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            mrs = json.loads(result.stdout)
            if mrs:
                return str(mrs[0].get("iid"))
        return None

    def upload_file(self, file_path: str, remote_name: Optional[str] = None) -> Optional[str]:
        """Upload a file to the GitLab project and return markdown image reference.

        Uses GitLab's project uploads API (POST /projects/:id/uploads).
        The returned markdown can be embedded directly in issue comments.
        """
        if not os.path.exists(file_path):
            print(f"Warning: File not found for upload: {file_path}", file=sys.stderr)
            return None

        repo_path = self.get_repo_path()
        encoded_path = repo_path.replace("/", "%2F")
        hostname = self._get_hostname()
        token = os.getenv("GITLAB_TOKEN") or os.getenv("GITLAB_ACCESS_TOKEN")

        if not token:
            print("Warning: No GITLAB_TOKEN set, cannot upload files", file=sys.stderr)
            return None

        try:
            result = subprocess.run(
                [
                    "curl", "-s",
                    "--request", "POST",
                    "--header", f"PRIVATE-TOKEN: {token}",
                    "--form", f"file=@{file_path}",
                    f"https://{hostname}/api/v4/projects/{encoded_path}/uploads",
                ],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                print(f"Warning: Upload failed: {result.stderr}", file=sys.stderr)
                return None

            data = json.loads(result.stdout)
            markdown = data.get("markdown")
            if markdown:
                print(f"Uploaded {os.path.basename(file_path)} to GitLab")
                return markdown
            else:
                print(f"Warning: Upload response missing markdown field: {result.stdout}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"Warning: Error uploading file: {e}", file=sys.stderr)
            return None

    def approve_mr(self, mr_number: str) -> tuple[bool, Optional[str]]:
        try:
            repo_path = self.get_repo_path()
        except Exception as e:
            return False, f"Failed to get repo info: {e}"
        result = subprocess.run(
            ["glab", "mr", "approve", mr_number, "-R", repo_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return False, result.stderr
        return True, None

    def merge_mr(self, mr_number: str, method: str = "squash") -> tuple[bool, Optional[str]]:
        try:
            repo_path = self.get_repo_path()
        except Exception as e:
            return False, f"Failed to get repo info: {e}"

        merge_cmd = ["glab", "mr", "merge", mr_number, "-R", repo_path, "--yes"]
        if method == "squash":
            merge_cmd.append("--squash")
        elif method == "rebase":
            merge_cmd.append("--rebase")

        result = subprocess.run(merge_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, result.stderr
        return True, None
