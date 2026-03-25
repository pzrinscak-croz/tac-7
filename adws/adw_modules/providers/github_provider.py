"""GitHub provider implementation using the gh CLI."""

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


class GitHubProvider(IssueProvider):
    """GitHub implementation of the issue provider interface."""

    def get_provider_name(self) -> str:
        return "github"

    def get_cli_name(self) -> str:
        return "gh"

    def get_mr_term(self) -> str:
        return "PR"

    def _get_env(self) -> Optional[dict]:
        """Get environment with GitHub token. Returns None to inherit parent env."""
        github_pat = os.getenv("GITHUB_PAT")
        if not github_pat:
            return None
        return {
            "GH_TOKEN": github_pat,
            "PATH": os.environ.get("PATH", ""),
        }

    def get_repo_path(self) -> str:
        """Extract owner/repo from GitHub URL."""
        url = self.get_repo_url()
        return url.replace("https://github.com/", "").replace(".git", "")

    def _parse_user(self, data: dict) -> IssueUser:
        return IssueUser(
            id=data.get("id"),
            login=data.get("login", ""),
            name=data.get("name"),
            is_bot=data.get("is_bot", False),
        )

    def _parse_label(self, data: dict) -> IssueLabel:
        return IssueLabel(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            color=data.get("color", ""),
            description=data.get("description"),
        )

    def _parse_comment(self, data: dict) -> IssueComment:
        return IssueComment(
            id=str(data.get("id", "")),
            author=self._parse_user(data.get("author", {})),
            body=data.get("body", ""),
            created_at=data.get("createdAt", ""),
            updated_at=data.get("updatedAt"),
        )

    def fetch_issue(self, issue_number: str, repo_path: str) -> Issue:
        cmd = [
            "gh", "issue", "view", issue_number, "-R", repo_path,
            "--json",
            "number,title,body,state,author,assignees,labels,milestone,comments,createdAt,updatedAt,closedAt,url",
        ]
        env = self._get_env()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if result.returncode != 0:
                print(result.stderr, file=sys.stderr)
                sys.exit(result.returncode)

            data = json.loads(result.stdout)
            return Issue(
                number=data["number"],
                title=data["title"],
                body=data.get("body", ""),
                state=data.get("state", ""),
                author=self._parse_user(data.get("author", {})),
                assignees=[self._parse_user(a) for a in data.get("assignees", [])],
                labels=[self._parse_label(l) for l in data.get("labels", [])],
                milestone=IssueMilestone(
                    id=str(data["milestone"]["id"]),
                    number=data["milestone"].get("number"),
                    title=data["milestone"]["title"],
                    description=data["milestone"].get("description"),
                    state=data["milestone"].get("state", ""),
                ) if data.get("milestone") else None,
                comments=[self._parse_comment(c) for c in data.get("comments", [])],
                created_at=data.get("createdAt", ""),
                updated_at=data.get("updatedAt", ""),
                closed_at=data.get("closedAt"),
                url=data.get("url", ""),
            )
        except FileNotFoundError:
            print("Error: GitHub CLI (gh) is not installed.", file=sys.stderr)
            print("\nTo install gh:", file=sys.stderr)
            print("  - macOS: brew install gh", file=sys.stderr)
            print("  - Linux: See https://github.com/cli/cli#installation", file=sys.stderr)
            print("\nAfter installation, authenticate with: gh auth login", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error parsing issue data: {e}", file=sys.stderr)
            sys.exit(1)

    def fetch_open_issues(self, repo_path: str) -> List[IssueListItem]:
        try:
            cmd = [
                "gh", "issue", "list", "--repo", repo_path,
                "--state", "open",
                "--json", "number,title,body,labels,createdAt,updatedAt",
                "--limit", "1000",
            ]
            env = self._get_env()
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
            issues_data = json.loads(result.stdout)
            issues = []
            for d in issues_data:
                issues.append(IssueListItem(
                    number=d["number"],
                    title=d["title"],
                    body=d.get("body", ""),
                    labels=[self._parse_label(l) for l in d.get("labels", [])],
                    created_at=d.get("createdAt", ""),
                    updated_at=d.get("updatedAt", ""),
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
        try:
            cmd = [
                "gh", "issue", "view", str(issue_number),
                "--repo", repo_path, "--json", "comments",
            ]
            env = self._get_env()
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
            data = json.loads(result.stdout)
            comments = data.get("comments", [])
            comments.sort(key=lambda c: c.get("createdAt", ""))
            return comments
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to fetch comments for issue #{issue_number}: {e.stderr}", file=sys.stderr)
            return []
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse comments JSON for issue #{issue_number}: {e}", file=sys.stderr)
            return []

    def make_issue_comment(self, issue_id: str, comment: str) -> None:
        repo_path = self.get_repo_path()
        if not comment.startswith(self.BOT_IDENTIFIER):
            comment = f"{self.BOT_IDENTIFIER} {comment}"

        cmd = ["gh", "issue", "comment", issue_id, "-R", repo_path, "--body", comment]
        env = self._get_env()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
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
        env = self._get_env()

        # Add label
        cmd = ["gh", "issue", "edit", issue_id, "-R", repo_path, "--add-label", "in_progress"]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            print(f"Note: Could not add 'in_progress' label: {result.stderr}")

        # Assign to self
        cmd = ["gh", "issue", "edit", issue_id, "-R", repo_path, "--add-assignee", "@me"]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode == 0:
            print(f"Assigned issue #{issue_id} to self")

    def check_mr_exists(self, branch_name: str) -> Optional[str]:
        try:
            repo_path = self.get_repo_path()
        except Exception:
            return None
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", repo_path, "--head", branch_name, "--json", "url"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            prs = json.loads(result.stdout)
            if prs:
                return prs[0]["url"]
        return None

    def get_mr_number(self, branch_name: str) -> Optional[str]:
        try:
            repo_path = self.get_repo_path()
        except Exception:
            return None
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", repo_path, "--head", branch_name,
             "--json", "number", "--limit", "1"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            prs = json.loads(result.stdout)
            if prs:
                return str(prs[0]["number"])
        return None

    def approve_mr(self, mr_number: str) -> tuple[bool, Optional[str]]:
        try:
            repo_path = self.get_repo_path()
        except Exception as e:
            return False, f"Failed to get repo info: {e}"
        result = subprocess.run(
            ["gh", "pr", "review", mr_number, "--repo", repo_path, "--approve",
             "--body", "ADW Ship workflow approved this PR after validating all state fields."],
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

        # Check mergeability
        result = subprocess.run(
            ["gh", "pr", "view", mr_number, "--repo", repo_path,
             "--json", "mergeable,mergeStateStatus"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return False, f"Failed to check PR status: {result.stderr}"

        pr_status = json.loads(result.stdout)
        if pr_status.get("mergeable") != "MERGEABLE":
            return False, f"PR is not mergeable. Status: {pr_status.get('mergeStateStatus', 'unknown')}"

        merge_cmd = [
            "gh", "pr", "merge", mr_number, "--repo", repo_path,
            f"--{method}",
            "--body", "Merged by ADW Ship workflow after successful validation.",
        ]
        result = subprocess.run(merge_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, result.stderr
        return True, None
