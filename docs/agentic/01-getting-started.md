# ADW Agentic Layer — Getting Started

## Prerequisites

Before you can run ADW workflows, ensure you have the following installed:

### Required Tools
- **`uv`** — Python package manager (Anthropic's recommendation). [Install here](https://docs.astral.sh/uv/getting-started/installation/).
- **`gh` CLI** — GitHub command-line tool. Installed via `brew install gh` or [download](https://cli.github.com/).
- **`claude` CLI** — Anthropic's Claude Code tool. Installed via `npm install -g @anthropic-ai/claude-code`.
- **`bun`** — JavaScript runtime (for frontend builds). Installed via `npm install -g bun` or [download](https://bun.sh/).

### Required Credentials

Create a `.env` file in the project root (copy from `.env.sample`):

```bash
# Required for GitHub operations
GITHUB_PAT=<your-personal-access-token>  # Create at https://github.com/settings/tokens
GITHUB_WEBHOOK_SECRET=<your-webhook-secret>  # Any string, used to validate GitHub webhooks

# Required for Claude API calls
ANTHROPIC_API_KEY=<your-api-key>  # Get from https://console.anthropic.com

# Required for webhook trigger
WEBHOOK_DOMAIN=<your-ngrok-or-tunnel-domain>  # e.g., https://abc123.ngrok.io
```

**GitHub Token Scopes**: When creating your PAT, ensure it has:
- `repo` — full control of repositories
- `workflow` — update GitHub Actions workflows

### Verify Environment

Run the health check to verify everything is set up:

```bash
/health_check
```

This command will validate:
- ✓ ANTHROPIC_API_KEY is set
- ✓ GITHUB_PAT is set
- ✓ Claude Code CLI is installed and working
- ✓ GitHub CLI is installed and authenticated
- ✓ Required Python packages are available
- ✓ SQLite database exists

If all checks pass, you're ready to proceed.

## First Run: Manual Workflow

Let's run a simple workflow manually via the CLI to understand the flow.

### Step 1: Create a Test Issue

Create a GitHub issue in the repository you want to work on. You can use any real issue, but for testing, create a simple one like:
```
Title: "Test ADW Workflow"
Body: "This is a test issue to verify ADW is working."
```

Note the issue number (e.g., #123).

### Step 2: Run the Plan Phase

```bash
cd /Users/pzrinscak/dev/idd/tac-7
uv run adws/adw_plan_iso.py 123
```

Replace `123` with your issue number. This will:
1. Generate an 8-char ADW ID (e.g., `a1b2c3d4`)
2. Create an isolated git worktree at `trees/a1b2c3d4/`
3. Allocate unique ports (e.g., backend 9100, frontend 9200)
4. Classify the issue (returns `/chore`, `/bug`, or `/feature`)
5. Generate a branch name (e.g., `chore-issue-123-a1b2c3d4-test-adw-workflow`)
6. Run the planner agent in the worktree
7. Create a spec file at `specs/issue-123-adw-a1b2c3d4-sdlc_planner-test-adw-workflow.md`
8. Commit and push the spec
9. Create/update a GitHub PR
10. Post progress comments to the GitHub issue

**Expected output**: The script will print the ADW ID and PR URL.

### Step 3: Inspect the Spec File

```bash
cat specs/issue-123-adw-a1b2c3d4-sdlc_planner-test-adw-workflow.md
```

You'll see a structured plan with:
- **Feature/Bug/Chore Description** — what the task is
- **Relevant Files** — which files to modify
- **Step-by-Step Tasks** — numbered implementation steps
- **Validation Commands** — commands the implementor will run to confirm success

### Step 4: Run the Implementation Phase

```bash
uv run adws/adw_build_iso.py 123 a1b2c3d4
```

This will:
1. Load the saved state
2. Validate the worktree still exists
3. Read the spec file
4. Run the implementor agent (Claude will follow the spec steps literally)
5. Commit changes
6. Push to the branch

### Step 5: Monitor the PR

Visit the GitHub PR that was created. You'll see:
- Commits from the ADW bot
- Comments showing progress (prefixed with `[ADW-AGENTS]`)
- Code changes made by the implementor agent

### Step 6: Cleanup (Optional)

If you want to remove the test worktree after you're done:

```bash
git worktree remove --force trees/a1b2c3d4
```

Or use the cleanup command:

```bash
/cleanup_worktrees specific a1b2c3d4
```

## Running Automated Triggers

Once you're comfortable with the manual flow, you can set up automated triggers.

### Trigger 1: Webhook (Real-Time)

Start the webhook server in one terminal:

```bash
uv run adws/adw_triggers/trigger_webhook.py
```

This starts a FastAPI server on `http://localhost:8001`. Now you need to expose it to the internet so GitHub can send webhooks.

**Using ngrok** (recommended for testing):
```bash
ngrok http 8001
```

This will give you a URL like `https://abc123.ngrok.io`. Configure the GitHub webhook:

1. Go to your repo → Settings → Webhooks → Add webhook
2. **Payload URL**: `https://abc123.ngrok.io/gh-webhook`
3. **Content type**: `application/json`
4. **Secret**: Set it to the value of `GITHUB_WEBHOOK_SECRET` in your `.env`
5. **Events**: Select "Issues" and "Issue comments"

Now, when you create an issue or comment with `adw_sdlc_iso` in the body, the webhook will trigger automatically.

### Trigger 2: Cron Polling (Periodic)

In another terminal, run the cron poller:

```bash
uv run adws/adw_triggers/trigger_cron.py
```

This polls GitHub every 20 seconds for:
- New issues without comments
- Issues where the latest comment is exactly `"adw"`

When found, it triggers the default workflow (`adw_plan_build_iso`).

## Workflow Invocation Methods

There are 4 ways to trigger a workflow:

### Method 1: GitHub Issue Body (Webhook)

Create an issue with the workflow command in the body:
```markdown
Title: "Add CSV export feature"
Body: "adw_sdlc_iso model_set heavy"
```

The webhook will:
1. Parse `adw_sdlc_iso` from the body
2. Extract `model_set=heavy`
3. Start the workflow

### Method 2: GitHub Comment (Webhook or Cron)

Comment on an existing issue:
```
/adw_plan_build_iso
```

or

```
adw_plan_build_review_iso model_set heavy adw_id a1b2c3d4
```

### Method 3: Direct CLI

```bash
# Run full SDLC
uv run adws/adw_sdlc_iso.py 123

# Run just plan + build
uv run adws/adw_plan_build_iso.py 123

# Run plan only
uv run adws/adw_plan_iso.py 123
```

### Method 4: Interactive Claude Code Slash Commands

Inside a Claude Code session, use any of the 28+ slash commands directly:

```
/feature 123 a1b2c3d4 '{"title":"...","body":"..."}'
/implement specs/issue-123-...md
/review a1b2c3d4 specs/issue-123-...md
```

## Understanding the Output

### Console Output

When you run a workflow, you'll see:
```
2026-03-24 10:15:23 [ADW-a1b2c3d4] Planning phase started
2026-03-24 10:15:45 [ADW-a1b2c3d4] Classifying issue...
2026-03-24 10:16:12 [ADW-a1b2c3d4] Issue classified as: /feature
2026-03-24 10:16:35 [ADW-a1b2c3d4] Generating branch name...
2026-03-24 10:16:52 [ADW-a1b2c3d4] Branch: feat-issue-123-a1b2c3d4-add-csv-export
2026-03-24 10:17:18 [ADW-a1b2c3d4] Running planner agent...
2026-03-24 10:19:45 [ADW-a1b2c3d4] Plan created at: specs/issue-123-adw-a1b2c3d4-sdlc_planner-add-csv-export.md
2026-03-24 10:20:12 [ADW-a1b2c3d4] PR created: https://github.com/owner/repo/pull/456
```

### State File

The execution state is saved to:
```bash
cat agents/a1b2c3d4/adw_state.json
```

Output:
```json
{
  "adw_id": "a1b2c3d4",
  "issue_number": 123,
  "branch_name": "feat-issue-123-a1b2c3d4-add-csv-export",
  "plan_file": "specs/issue-123-adw-a1b2c3d4-sdlc_planner-add-csv-export.md",
  "issue_class": "feature",
  "worktree_path": "/Users/pzrinscak/dev/idd/tac-7/trees/a1b2c3d4",
  "backend_port": 9100,
  "frontend_port": 9200,
  "model_set": "base",
  "all_adws": ["adw_plan_iso", "adw_build_iso"]
}
```

### Session Logs

Claude Code sessions are logged to:
```bash
ls logs/
# Output: 1f175484-3496-487a-8719-601dff344eb0/  41830f2a-8522-4dba-ad1c-8769fdf42e11/  ...

cat logs/1f175484-3496-487a-8719-601dff344eb0/chat.json
```

See `07-operations.md` for how to read these logs.

## ZTE (Zero Touch Execution) — Important Safety Note

The workflow `adw_sdlc_ZTE_iso` includes an automatic merge phase. It **will merge code to main without human review**. Only use this workflow when:

1. The issue is well-scoped and low-risk
2. You have reviewed the spec before triggering
3. All tests pass

To trigger ZTE, you **must** use uppercase `ZTE` in the GitHub body:

```markdown
Title: "Fix typo in README"
Body: "/adw_sdlc_ZTE_iso"  ← ✓ triggers ZTE
       "/adw_sdlc_zte_iso"  ← ✗ does NOT trigger (lowercase)
```

This safeguard prevents accidental auto-merges.

## Troubleshooting

### Claude Code CLI Not Found

```bash
npm install -g @anthropic-ai/claude-code
which claude
```

### GitHub API Failures

Check your token:
```bash
gh auth status
gh auth login
```

### Port Conflicts

If you get "port already in use", the system will automatically find the next available port. To manually free a port:

```bash
scripts/check_ports.sh
lsof -i :9100  # See what's using port 9100
kill -9 <PID>  # Kill the process
```

### Worktree Issues

List existing worktrees:
```bash
git worktree list
```

Remove a stuck worktree:
```bash
git worktree remove --force trees/a1b2c3d4
rm -rf trees/a1b2c3d4  # If the above fails
```

## Next Steps

- **Core Concepts**: Read `02-core-concepts.md` to understand ADW ID, state, worktrees, model sets
- **Command Reference**: Read `04-slash-commands.md` to see all 28 slash commands
- **Operations**: Read `07-operations.md` to learn how to monitor, debug, and maintain the system
