# ADW Agentic Layer — Triggering Workflows

This document explains how to start ADW workflows: via webhook, cron polling, CLI, or interactive Claude Code.

## Overview: Four Trigger Methods

| Method | Type | Speed | Manual Effort | Best For |
|--------|------|-------|---------------|----------|
| Webhook | Real-time | 1s response | None (automatic) | Production GitHub integration |
| Cron | Polling | 20s delay | None (automatic) | Fallback when webhook unavailable |
| CLI | Direct | Instant | Batch scripts or local testing | Development, manual testing |
| Claude Code | Interactive | Manual | Per-command | Debugging, experimenting |

## Trigger 1: Webhook (Real-Time)

GitHub webhook is the recommended trigger for production. It responds in real-time to issue creation or comments.

### Setup

#### Step 1: Configure Environment

```bash
# In .env
GITHUB_PAT=ghp_...                  # Your GitHub personal access token
GITHUB_WEBHOOK_SECRET=your-secret   # Any random string for HMAC validation
WEBHOOK_DOMAIN=https://abc123.ngrok.io  # Your public domain
```

#### Step 2: Start the Webhook Server

```bash
uv run adws/adw_triggers/trigger_webhook.py
# Starts FastAPI on http://localhost:8001
```

#### Step 3: Expose to Internet

Use ngrok or similar to expose local port 8001:

```bash
ngrok http 8001
# Output: Forwarding https://abc123.ngrok.io -> http://localhost:8001
```

Update `WEBHOOK_DOMAIN` in `.env`:
```bash
WEBHOOK_DOMAIN=https://abc123.ngrok.io
```

#### Step 4: Register GitHub Webhook

1. Go to your repository → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://abc123.ngrok.io/gh-webhook`
3. **Content type**: `application/json`
4. **Secret**: Set to `GITHUB_WEBHOOK_SECRET` from `.env`
5. **Which events?**: Select:
   - ☑ Issues
   - ☑ Issue comments
6. **Active**: ✓ Checked
7. Click **Add webhook**

### How Webhook Works

When someone creates an issue or comments on an issue:

```
GitHub sends POST /gh-webhook with:
{
  "action": "opened" (for new issues) or "created" (for comments),
  "issue": { "number": 123, "body": "..." },
  "comment": { "body": "..." } (if comment event)
}

trigger_webhook.py receives request:
├─ Verifies HMAC signature using GITHUB_WEBHOOK_SECRET
├─ Filters out bot comments (pattern: [ADW-AGENTS])
├─ Filters out progress comments (pattern: ^[a-f0-9]{8}_\w+)
├─ Searches body/comment for "adw_" keyword
├─ Calls /classify_adw to extract workflow + model_set
├─ Creates ADWState with issue_number, adw_id, model_set
├─ Spawns: uv run adws/{workflow}.py {issue_number} {adw_id}
│        as background process (start_new_session=True)
└─ Returns 200 OK immediately (doesn't wait for workflow)
```

### Workflow Selection

The webhook uses `/classify_adw` command to extract the workflow from issue body/comment.

**Patterns recognized**:

```markdown
# Triggers adw_plan_build_iso (default if just "adw")
Issue body: "adw"
Issue body: "adw_plan_build_iso"

# Triggers full SDLC
Issue body: "adw_sdlc_iso"

# Triggers ZTE (UPPERCASE required!)
Issue body: "adw_sdlc_ZTE_iso"
Issue body: "/adw_sdlc_ZTE_iso"

# With model set override
Issue body: "adw_sdlc_iso model_set heavy"
Issue body: "adw_plan_build_review_iso model_set base"

# With explicit ADW ID (for dependent phases)
Comment: "adw_build_iso adw_id abc12345"
Comment: "adw_review_iso adw_id abc12345"
```

### Security: Loop Prevention

The webhook has built-in protection against infinite loops:

```python
# Ignore bot's own comments
if "[ADW-AGENTS]" in comment.body:
    return  # Skip this comment

# Ignore progress comment pattern
if re.match(r"^[a-f0-9]{8}_\w+[_:]", comment.body):
    return  # Skip progress comments
```

This prevents:
- Bot creates PR → bot posts PR URL comment → webhook sees comment → triggers again
- Bot posts "Building..." progress → triggers again

### ZTE Safety: Uppercase Requirement

The `/adw_sdlc_ZTE_iso` workflow **auto-merges to main**. To prevent accidental triggers:

```python
# In classify_adw.md
if "adw_sdlc_ZTE_iso" in body:     # ✓ triggers
    return "adw_sdlc_ZTE_iso"

if "adw_sdlc_zte_iso" in body:     # ✗ does NOT trigger
    return None
```

Only explicit uppercase `ZTE` triggers auto-merge. Lowercase is ignored.

### Example: Trigger via Webhook

**User opens issue**:
```markdown
Title: "Add CSV export feature"
Body: "adw_sdlc_iso model_set heavy"
```

**GitHub sends webhook** → `trigger_webhook.py` receives it

**Webhook detects**: `adw_sdlc_iso` in body

**Calls `/classify_adw`**:
```json
{
  "adw_workflow": "adw_sdlc_iso",
  "adw_id": "490eb6b5",
  "model_set": "heavy"
}
```

**Spawns subprocess**:
```bash
uv run adws/adw_sdlc_iso.py 123 490eb6b5
```

**Returns 200 OK immediately** (doesn't wait)

**Workflow runs in background** over ~2 minutes

## Trigger 2: Cron Polling (Fallback)

If webhook is unavailable (no ngrok, no internet), use the cron poller as a fallback.

### Setup

```bash
uv run adws/adw_triggers/trigger_cron.py
# Polls GitHub every 20 seconds
```

### How It Works

Every 20 seconds, the cron trigger:

```python
open_issues = fetch_open_issues()  # gh issue list --state open

for issue in open_issues:
    # Check if issue should be processed
    if should_process_issue(issue):
        # Trigger default workflow
        subprocess.run(["uv", "run", "adws/adw_plan_build_iso.py", issue.number])

def should_process_issue(issue):
    comments = fetch_issue_comments(issue.number)

    # Condition 1: Issue has no comments (new issue)
    if len(comments) == 0:
        return True

    # Condition 2: Latest comment is exactly "adw"
    latest_comment = comments[-1]
    if latest_comment.body.strip() == "adw":
        return True

    # Skip if already processed this session
    if issue.number in processed_issues:
        return False

    return False
```

### Workflow Selection via Comment

The cron poller always runs `adw_plan_build_iso` by default. To trigger a different workflow:

```markdown
# Comment on the issue
adw_sdlc_iso
```

The cron poller detects `adw_` keyword and uses `/classify_adw` to select the workflow.

### Limitations

- **20-second delay**: Not real-time
- **No model_set support**: Uses default `base`
- **Default workflow**: Can't easily trigger ZTE

**Recommendation**: Use webhook for production, cron as fallback.

## Trigger 3: Direct CLI

Run workflow scripts directly for manual execution or scripting.

### Single Phase

```bash
# Run planning phase only
uv run adws/adw_plan_iso.py 123

# Specify ADW ID (if reusing)
uv run adws/adw_plan_iso.py 123 abc12345
```

### Pipeline Workflows

```bash
# Plan + Build
uv run adws/adw_plan_build_iso.py 123

# Plan + Build + Test
uv run adws/adw_plan_build_test_iso.py 123

# Full SDLC (Plan + Build + Test + Review + Document)
uv run adws/adw_sdlc_iso.py 123

# Full SDLC + Auto-Merge (ZTE)
uv run adws/adw_sdlc_zte_iso.py 123

# With flags
uv run adws/adw_sdlc_iso.py 123 --skip-e2e --skip-resolution
```

### Batch Scripting

```bash
#!/bin/bash
# Process multiple issues
for issue_number in 123 124 125; do
    uv run adws/adw_plan_build_iso.py $issue_number
    # Wait for workflow to complete
    sleep 5
done
```

### Return Codes

```python
# 0 = success
# 1 = workflow phase failed
# 2 = configuration error
# 127 = file not found
```

Use in scripts:

```bash
if uv run adws/adw_plan_iso.py 123; then
    echo "Plan succeeded"
    uv run adws/adw_build_iso.py 123 $adw_id
else
    echo "Plan failed"
    exit 1
fi
```

## Trigger 4: Interactive Claude Code

Use slash commands in a Claude Code session for interactive work.

### Basic Usage

```
/prime        # Orient to codebase
/feature 123 a1b2c3d4 '{"title":"...","body":"..."}'  # Create plan
/implement specs/issue-123-...md    # Implement plan
/review a1b2c3d4 specs/...md        # Review implementation
/test         # Run test suite
/test_e2e a1b2c3d4 issue_classifier test_e2e_basic.md  # E2E test
/start        # Start the app
```

### Advantages

- **Iterative**: See results immediately
- **Debuggable**: Inspect intermediate outputs
- **Flexible**: Run individual commands or skip phases
- **Learning**: Great for understanding how each phase works

### Disadvantages

- **Manual**: Requires human interaction
- **Slow**: Each command is interactive
- **Not scalable**: Can't run 15 workflows in parallel

## Model Set Selection

By default, workflows use `"base"` model set (cheaper, adequate quality).

For complex tasks, override to `"heavy"` (more expensive, better quality):

### Via Webhook

```markdown
Issue body: "adw_sdlc_iso model_set heavy"
```

### Via Cron

Cron poller doesn't support model_set override (always uses base).

### Via CLI

Currently CLI doesn't support model_set flag. Must edit `.env` or hardcode in state file.

### Via Interactive Claude Code

Model selection is automatic based on command:

```
haiku     — /classify_issue, /commit, /generate_branch_name (cheap)
sonnet    — /feature, /implement, /review (default)
opus      — n/a in interactive mode (use base model set)
```

## ZTE (Zero Touch Execution) Safety

The `adw_sdlc_ZTE_iso` workflow **auto-merges code to main**. Safety mechanisms:

### 1. Explicit Uppercase Trigger

```python
# Only this triggers ZTE:
issue.body.contains("adw_sdlc_ZTE_iso")  # ✓

# These do NOT trigger ZTE:
issue.body.contains("adw_sdlc_zte_iso")  # ✗ lowercase
issue.body.contains("ZTE_iso")           # ✗ missing prefix
```

### 2. Warning Comment

When ZTE starts, it posts to the issue:

```markdown
🚀 **Zero Touch Execution started** for issue #123

This workflow will auto-merge your code if all phases pass.

**If blockers occur, the workflow will abort and post the reason.**
```

### 3. Strict Validation

ZTE aborts immediately on:
- Test failure
- Review blocker (severity: blocker)

Documentation failure does NOT abort (less critical).

### 4. Approval Required

If you want to require human approval, do NOT use ZTE. Use `adw_sdlc_iso` instead.

## Comparing Trigger Methods

### When to Use Webhook

✓ Production deployments
✓ Real-time GitHub integration
✓ Frequent, automated workflows
✓ Multiple users triggering issues

**Setup**: 5 minutes + ngrok tunnel

### When to Use Cron

✓ Testing without ngrok
✓ Fallback for webhook failures
✓ Simple "run daily" automation

**Limitations**: 20-second delay, default model set, no ZTE support

### When to Use CLI

✓ Development and debugging
✓ Batch processing (scripts)
✓ Testing new issue types
✓ Specific phase debugging

**Limitations**: Manual invocation, slower feedback

### When to Use Interactive Claude Code

✓ Learning how ADW works
✓ Debugging a stuck workflow
✓ Iterative experimentation
✓ Manual code review and refinement

**Limitations**: Not scalable, requires human attention

## Monitoring Active Workflows

### Method 1: GitHub Issue

Check the issue for comments from `[ADW-AGENTS]`:

```markdown
[ADW-AGENTS] ✅ Planning phase completed
- Branch: feat-issue-123-a1b2c3d4-csv-export
- Spec: specs/issue-123-adw-a1b2c3d4-...md
- PR: https://github.com/owner/repo/pull/456

[ADW-AGENTS] ✅ Building phase completed

[ADW-AGENTS] ⚠️ Testing phase has failures
Auto-fixing...

[ADW-AGENTS] ✅ Testing phase recovered

[ADW-AGENTS] ✅ Review phase completed (all issues resolved)

[ADW-AGENTS] ✅ Documentation generated

[ADW-AGENTS] 🎉 Merged to production!
```

### Method 2: File System

Check for active state file:

```bash
ls agents/*/adw_state.json
cat agents/a1b2c3d4/adw_state.json
```

Check logs:

```bash
tail -f logs/*/user_prompt_submit.json
tail -f agents/a1b2c3d4/sdlc_*/raw_output.jsonl
```

### Method 3: Worktrees

List active worktrees:

```bash
git worktree list
# Output:
# /path/to/repo       (bare)
# /path/to/repo/trees/a1b2c3d4   (detached)
# /path/to/repo/trees/490eb6b5   (detached)
```

### Method 4: Processes

```bash
ps aux | grep "adw_.*_iso.py"
# Shows which phase scripts are running
```

## Troubleshooting Triggers

### Issue: Webhook not responding

```bash
# Check webhook server is running
curl http://localhost:8001/health

# Check ngrok tunnel
ngrok status

# Verify webhook is registered
gh repo view --web  # Check Settings → Webhooks
```

### Issue: Comment not triggering workflow

```bash
# Verify comment contains "adw_" keyword
# Verify it's not prefixed with [ADW-AGENTS]
# Verify it's not a progress comment
# Try the exact pattern: "adw_plan_build_iso"
```

### Issue: ZTE not triggering

```bash
# Verify you used UPPERCASE "ZTE"
# Not: "adw_sdlc_zte_iso" (lowercase)
# Use: "adw_sdlc_ZTE_iso" (uppercase)
```

### Issue: Wrong model set selected

```bash
# Check state file
cat agents/{adw_id}/adw_state.json | jq .model_set

# For webhook, include in issue body
"adw_sdlc_iso model_set heavy"
```

## Next Steps

- **Operations**: Read `07-operations.md` to monitor and debug running workflows
- **Extending**: Read `08-extending.md` to add custom triggers
