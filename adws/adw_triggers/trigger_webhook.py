#!/usr/bin/env -S uv run
# /// script
# dependencies = ["fastapi", "uvicorn", "python-dotenv"]
# ///

"""
Webhook Trigger - AI Developer Workflow (ADW)

FastAPI webhook endpoint that receives GitHub or GitLab issue events and triggers
ADW workflows. Responds immediately to meet webhook timeout constraints by
launching workflows in the background.

Supports:
- GitHub webhooks (X-GitHub-Event header)
- GitLab webhooks (X-Gitlab-Event header)

Usage: uv run trigger_webhook.py

Environment Requirements:
- PORT: Server port (default: 8001)
- ADW_PROVIDER: "github" or "gitlab" (auto-detected if not set)
- All workflow requirements (GITHUB_PAT or GITLAB_TOKEN, ANTHROPIC_API_KEY, etc.)
"""

import os
import re
import subprocess
import sys
from typing import Optional, Tuple
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adw_modules.utils import make_adw_id, setup_logger, get_safe_subprocess_env
from adw_modules.github import make_issue_comment, ADW_BOT_IDENTIFIER
from adw_modules.workflow_ops import extract_adw_info, AVAILABLE_ADW_WORKFLOWS
from adw_modules.state import ADWState

# Load environment variables
load_dotenv()

# Configuration
PORT = int(os.getenv("PORT", "8001"))

# Dependent workflows that require existing worktrees
# These cannot be triggered directly via webhook
DEPENDENT_WORKFLOWS = [
    "adw_build_iso",
    "adw_test_iso",
    "adw_review_iso",
    "adw_document_iso",
    "adw_ship_iso",
]

# Create FastAPI app
app = FastAPI(
    title="ADW Webhook Trigger", description="GitHub/GitLab webhook endpoint for ADW"
)

print(f"Starting ADW Webhook Trigger on port {PORT}")

# Pattern matching workflow progress comments: {8-char-hex}_{agent_name}: or {8-char-hex}_{agent_name}_
ADW_PROGRESS_PATTERN = re.compile(r'^[a-f0-9]{8}_\w+[_:]')


def _parse_github_event(event_type: str, payload: dict) -> Tuple[Optional[str], Optional[int], str, str]:
    """Parse GitHub webhook payload.
    Returns (action_type, issue_number, content_to_check, trigger_reason_prefix)
    action_type is 'issue_opened', 'comment_created', or None
    """
    action = payload.get("action", "")
    issue = payload.get("issue", {})
    issue_number = issue.get("number")

    if event_type == "issues" and action == "opened" and issue_number:
        return "issue_opened", issue_number, issue.get("body", ""), "New issue"

    if event_type == "issue_comment" and action == "created" and issue_number:
        comment = payload.get("comment", {})
        return "comment_created", issue_number, comment.get("body", ""), "Comment"

    return None, issue_number, "", ""


def _parse_gitlab_event(event_type: str, payload: dict) -> Tuple[Optional[str], Optional[int], str, str]:
    """Parse GitLab webhook payload.
    Returns (action_type, issue_number, content_to_check, trigger_reason_prefix)

    GitLab event types:
    - "Issue Hook" with action "open" → new issue
    - "Note Hook" with noteable_type "Issue" → issue comment
    """
    if event_type == "Issue Hook":
        attrs = payload.get("object_attributes", {})
        action = attrs.get("action", "")
        issue_number = attrs.get("iid")
        if action == "open" and issue_number:
            return "issue_opened", issue_number, attrs.get("description", ""), "New issue"

    elif event_type == "Note Hook":
        attrs = payload.get("object_attributes", {})
        noteable_type = attrs.get("noteable_type", "")
        if noteable_type == "Issue":
            issue = payload.get("issue", {})
            issue_number = issue.get("iid")
            if issue_number:
                return "comment_created", issue_number, attrs.get("note", ""), "Comment"

    return None, None, "", ""


def _detect_webhook_source(request: Request) -> str:
    """Detect if webhook is from GitHub or GitLab based on headers."""
    if request.headers.get("X-Gitlab-Event"):
        return "gitlab"
    if request.headers.get("X-GitHub-Event"):
        return "github"
    # Fallback: check for GitLab-specific fields
    return "github"


async def _process_webhook(request: Request):
    """Unified webhook handler for both GitHub and GitLab."""
    try:
        payload = await request.json()
        source = _detect_webhook_source(request)

        if source == "gitlab":
            event_type = request.headers.get("X-Gitlab-Event", "")
            action_type, issue_number, content_to_check, reason_prefix = _parse_gitlab_event(event_type, payload)
        else:
            event_type = request.headers.get("X-GitHub-Event", "")
            action_type, issue_number, content_to_check, reason_prefix = _parse_github_event(event_type, payload)

        print(f"Received {source} webhook: event={event_type}, action={action_type}, issue={issue_number}")

        workflow = None
        provided_adw_id = None
        model_set = None
        trigger_reason = ""

        if action_type == "issue_opened" and issue_number:
            if ADW_BOT_IDENTIFIER in content_to_check:
                print("Ignoring ADW bot issue to prevent loop")
            elif "adw_" in content_to_check.lower():
                temp_id = make_adw_id()
                extraction_result = extract_adw_info(content_to_check, temp_id)
                if extraction_result.has_workflow:
                    workflow = extraction_result.workflow_command
                    provided_adw_id = extraction_result.adw_id
                    model_set = extraction_result.model_set
                    trigger_reason = f"{reason_prefix} with {workflow} workflow"

        elif action_type == "comment_created" and issue_number:
            print(f"Comment body: '{content_to_check[:100]}'")
            if ADW_BOT_IDENTIFIER in content_to_check:
                print("Ignoring ADW bot comment to prevent loop")
            elif ADW_PROGRESS_PATTERN.match(content_to_check):
                print("Ignoring workflow progress comment to prevent loop")
            elif "adw_" in content_to_check.lower():
                temp_id = make_adw_id()
                extraction_result = extract_adw_info(content_to_check, temp_id)
                if extraction_result.has_workflow:
                    workflow = extraction_result.workflow_command
                    provided_adw_id = extraction_result.adw_id
                    model_set = extraction_result.model_set
                    trigger_reason = f"{reason_prefix} with {workflow} workflow"

        # Validate workflow constraints
        if workflow in DEPENDENT_WORKFLOWS:
            if not provided_adw_id:
                print(f"{workflow} is a dependent workflow that requires an existing ADW ID")
                try:
                    make_issue_comment(
                        str(issue_number),
                        f"Error: `{workflow}` is a dependent workflow that requires an existing ADW ID.\n\n"
                        f"Provide the ADW ID in your comment, e.g.: `{workflow} adw-12345678`",
                    )
                except Exception as e:
                    print(f"Failed to post error comment: {e}")
                workflow = None

        if workflow:
            adw_id = provided_adw_id or make_adw_id()

            # Create/update state
            if provided_adw_id:
                state = ADWState.load(provided_adw_id)
                if state:
                    state.update(issue_number=str(issue_number), model_set=model_set)
                else:
                    state = ADWState(provided_adw_id)
                    state.update(adw_id=provided_adw_id, issue_number=str(issue_number), model_set=model_set)
                state.save("webhook_trigger")
            else:
                state = ADWState(adw_id)
                state.update(adw_id=adw_id, issue_number=str(issue_number), model_set=model_set)
                state.save("webhook_trigger")

            logger = setup_logger(adw_id, "webhook_trigger")
            logger.info(f"Detected workflow: {workflow} from {source} (content: {content_to_check[:100]}...)")
            if provided_adw_id:
                logger.info(f"Using provided ADW ID: {provided_adw_id}")

            try:
                make_issue_comment(
                    str(issue_number),
                    f"ADW Webhook: Detected `{workflow}` workflow request\n\n"
                    f"Starting workflow with ID: `{adw_id}`\n"
                    f"Workflow: `{workflow}`\n"
                    f"Model Set: `{model_set}`\n"
                    f"Source: `{source}`\n"
                    f"Reason: {trigger_reason}\n\n"
                    f"Logs will be available at: `agents/{adw_id}/{workflow}/`",
                )
            except Exception as e:
                logger.warning(f"Failed to post issue comment: {e}")

            # Launch workflow
            script_dir = os.path.dirname(os.path.abspath(__file__))
            adws_dir = os.path.dirname(script_dir)
            repo_root = os.path.dirname(adws_dir)
            trigger_script = os.path.join(adws_dir, f"{workflow}.py")

            cmd = ["uv", "run", trigger_script, str(issue_number), adw_id]

            print(f"Launching {workflow} for issue #{issue_number}")
            print(f"Command: {' '.join(cmd)} (reason: {trigger_reason})")
            print(f"Working directory: {repo_root}")

            process = subprocess.Popen(
                cmd,
                cwd=repo_root,
                env=get_safe_subprocess_env(),
                start_new_session=True,
            )

            print(f"Background process started for issue #{issue_number} with ADW ID: {adw_id}")

            return {
                "status": "accepted",
                "source": source,
                "issue": issue_number,
                "adw_id": adw_id,
                "workflow": workflow,
                "message": f"ADW {workflow} triggered for issue #{issue_number}",
                "reason": trigger_reason,
                "logs": f"agents/{adw_id}/{workflow}/",
            }
        else:
            print(f"Ignoring {source} webhook: event={event_type}, action={action_type}, issue={issue_number}")
            return {
                "status": "ignored",
                "source": source,
                "reason": f"Not a triggering event (event={event_type}, action={action_type})",
            }

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error", "message": "Internal error processing webhook"}


# GitHub webhook endpoint (original)
@app.post("/gh-webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook events."""
    return await _process_webhook(request)


# GitLab webhook endpoint
@app.post("/gl-webhook")
async def gitlab_webhook(request: Request):
    """Handle GitLab webhook events."""
    return await _process_webhook(request)


# Unified endpoint (auto-detects source)
@app.post("/webhook")
async def unified_webhook(request: Request):
    """Handle webhook events from any supported provider."""
    return await _process_webhook(request)


@app.get("/health")
async def health():
    """Health check endpoint - runs comprehensive system health check."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        health_check_script = os.path.join(
            os.path.dirname(script_dir), "adw_tests", "health_check.py"
        )

        result = subprocess.run(
            ["uv", "run", health_check_script],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(script_dir),
        )

        print("=== Health Check Output ===")
        print(result.stdout)
        if result.stderr:
            print("=== Health Check Errors ===")
            print(result.stderr)

        output_lines = result.stdout.strip().split("\n")
        is_healthy = result.returncode == 0

        warnings = []
        errors = []
        capturing_warnings = False
        capturing_errors = False

        for line in output_lines:
            if "Warnings:" in line:
                capturing_warnings = True
                capturing_errors = False
                continue
            elif "Errors:" in line:
                capturing_errors = True
                capturing_warnings = False
                continue
            elif "Next Steps:" in line:
                break

            if capturing_warnings and line.strip().startswith("-"):
                warnings.append(line.strip()[2:])
            elif capturing_errors and line.strip().startswith("-"):
                errors.append(line.strip()[2:])

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "adw-webhook-trigger",
            "health_check": {
                "success": is_healthy,
                "warnings": warnings,
                "errors": errors,
                "details": "Run health_check.py directly for full report",
            },
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "unhealthy",
            "service": "adw-webhook-trigger",
            "error": "Health check timed out",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "adw-webhook-trigger",
            "error": f"Health check failed: {str(e)}",
        }


if __name__ == "__main__":
    print(f"Starting server on http://0.0.0.0:{PORT}")
    print(f"Webhook endpoints:")
    print(f"  POST /webhook     (auto-detect GitHub/GitLab)")
    print(f"  POST /gh-webhook  (GitHub)")
    print(f"  POST /gl-webhook  (GitLab)")
    print(f"Health check: GET /health")

    uvicorn.run(app, host="0.0.0.0", port=PORT)
