# ADW Agentic Layer — Operations & Monitoring

This document explains how to monitor, debug, and maintain ADW workflows in production.

## Three Core Directories: Quick Reference

ADW uses three main directories for different purposes:

| Directory | Purpose | Size | Lifecycle |
|-----------|---------|------|-----------|
| `agents/{adw_id}/` | Persistent state + agent logs | 2.1 MB | Kept forever (archive-able) |
| `logs/{session_id}/` | Claude Code hook telemetry | 6.9 MB | Kept for debugging (rotatable) |
| `trees/{adw_id}/` | Isolated git worktree | 327 MB | Cleaned up when workflow complete |

**What each stores**:
- **agents/** — State, prompts sent, Claude's responses (JSONL logs)
- **logs/** — Tool calls, permission checks, full session transcript
- **trees/** — Complete repo copy with isolated branch, code changes, test DB

**Which to examine when**:
- **Debugging Claude behavior** → `agents/{adw_id}/*/raw_output.jsonl` or `logs/*/chat.json`
- **Debugging tool calls** → `logs/{session_id}/pre_tool_use.json` (security checks)
- **Debugging code changes** → `trees/{adw_id}` (git diff, modified files)
- **Understanding workflow state** → `agents/{adw_id}/adw_state.json` (10 key fields)

## Logging Architecture

ADW uses two logging systems working together:

### 1. Claude Code Hook Logs (`logs/`)

**What**: Session-level telemetry from Claude Code itself

**Location**: `logs/{session_id}/` (UUID per Claude Code session, e.g., `1f175484-3496-487a-8719-601dff344eb0`)

**Size**: ~6.9 MB total across all sessions (107 files)

**Files per session**:
- `user_prompt_submit.json` — Every user message (JSONL format, newline-delimited)
- `pre_tool_use.json` — Every tool call before execution (JSONL format)
- `post_tool_use.json` — Every tool result after execution (JSONL format)
- `chat.json` — Full session transcript (converted from JSONL at session end)
- `stop.json` — Session end event with timestamp and last message
- `notification.json` — Permission prompts and idle alerts (JSONL)

**Key fields in pre_tool_use.json**:
```json
{
  "session_id": "1f175484-3496-487a-8719-601dff344eb0",
  "cwd": "/Users/pzrinscak/dev/idd/tac-7",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Read",
  "tool_input": {"file_path": "/path/to/file"},
  "tool_use_id": "toolu_01..."
}
```

**Example session directory**:
```bash
ls logs/1f175484-3496-487a-8719-601dff344eb0/
# chat.json                    ← Full conversation transcript
# notification.json            ← Permission prompts
# post_tool_use.json          ← Tool results
# pre_tool_use.json           ← Tool calls (security checks here)
# stop.json                   ← Session end event
# user_prompt_submit.json     ← User prompts
```

### 2. ADW Agent Logs (`agents/`)

**What**: Per-run state and agent session output for each ADW workflow

**Location**: `agents/{adw_id}/` (e.g., `agents/b5facb99/`)

**Size**: ~2.1 MB total (stores state + JSONL logs, not raw worktree changes)

**Root files**:
- `adw_state.json` — Persistent workflow state (10 fields, single JSON object, NOT newline-delimited)

**Agent directories** (one per phase/agent):
- `adw_plan_iso/` → Planning phase logs
- `adw_build_iso/` → Implementation phase logs
- `sdlc_planner/` → Planner agent output
- `sdlc_implementor/` → Implementor agent output
- `issue_classifier/` → Classification agent
- `branch_generator/` → Branch naming agent
- `reviewer/` → Review agent
- `documenter/` → Documentation agent
- Other agents as needed (ops, pr_creator, etc.)

**Files in each agent directory**:
```
agents/{adw_id}/{agent_name}/
├── raw_output.jsonl        ← Claude Code session JSONL (streaming)
├── raw_output.json         ← Converted to clean JSON
├── prompts/
│   └── {command}.txt       ← The prompt that was sent to Claude
└── execution.log           ← Phase script logs (DEBUG level)
```

**Example directory tree**:
```bash
agents/b5facb99/
├── adw_state.json                          ← Single state file
├── adw_build_iso/
│   └── execution.log
├── adw_plan_iso/
│   └── execution.log
├── branch_generator/
│   ├── prompts/
│   │   └── generate_branch_name.txt
│   ├── raw_output.json
│   └── raw_output.jsonl
├── issue_classifier/
│   ├── prompts/
│   │   └── classify_issue.txt
│   ├── raw_output.json
│   └── raw_output.jsonl
├── ops/
│   ├── prompts/
│   │   └── install_worktree.txt
│   ├── raw_output.json
│   └── raw_output.jsonl
├── pr_creator/
│   ├── prompts/
│   │   └── pull_request.txt
│   ├── raw_output.json
│   └── raw_output.jsonl
├── sdlc_planner/
│   ├── prompts/
│   │   └── feature.txt      ← The planning prompt sent
│   ├── raw_output.json
│   └── raw_output.jsonl     ← Claude's streaming response
└── sdlc_implementor/
    ├── prompts/
    │   └── implement.txt
    └── raw_output.jsonl

# Note: screenshot dirs may exist for review phase
# agents/b5facb99/reviewer/review_img/ (if /review captures screenshots)
```

**State file anatomy**:
```bash
cat agents/b5facb99/adw_state.json
# {
#   "adw_id": "b5facb99",
#   "issue_number": "1",
#   "branch_name": "feature-issue-1-adw-b5facb99-...",
#   "plan_file": "specs/issue-1-adw-b5facb99-...",
#   "issue_class": "/feature",
#   "worktree_path": "/Users/.../trees/b5facb99",
#   "backend_port": 9112,
#   "frontend_port": 9212,
#   "model_set": "base",
#   "all_adws": ["adw_plan_iso"]
# }
```

## Reading Logs

### Hook Logs (`logs/`)

**Find session ID**: Each Claude Code session writes its own session ID to logs:

```bash
# Find most recent session
ls -lt logs/ | head -1

# Or find by date
ls logs/ | grep 2026-03-24
```

**Read tool calls**:
```bash
cat logs/{session_id}/pre_tool_use.json | python -m json.tool | head -50

# Output:
# [
#   {
#     "timestamp": "2026-03-24T10:15:23.456",
#     "session_id": "1f175484-...",
#     "tool_name": "Read",
#     "tool_input": {
#       "file_path": "app/server/main.py"
#     },
#     "cwd": "/path/to/tac-7/trees/a1b2c3d4",
#     "permission_mode": "auto"
#   }
# ]
```

**Read full session transcript**:
```bash
cat logs/{session_id}/chat.json | python -m json.tool

# Structured conversation with all messages and tool uses
```

**Troubleshoot security blocks**:
```bash
# Pre-tool hook blocked a tool if exit code = 2
# Check what was blocked:
grep -i "error" logs/{session_id}/*.json

# Example: .env access attempt
# {
#   "timestamp": "...",
#   "tool_name": "Read",
#   "tool_input": {"file_path": ".env"},
#   "error": "Access denied: .env files cannot be read"
# }
```

### Agent Logs (`agents/`)

**Check overall state**:
```bash
cat agents/{adw_id}/adw_state.json | python -m json.tool

# Shows:
# - Which phases ran (all_adws list)
# - Current branch, worktree path, ports
# - Model set used
# - Plan file location
```

**Check phase execution**:
```bash
# See what each phase agent said
cat agents/{adw_id}/sdlc_planner/execution.log
# Timestamps, info/debug/error messages from the Python script

# See raw Claude output (JSONL format)
head -20 agents/{adw_id}/sdlc_planner/raw_output.jsonl | python -m json.tool
```

**Correlate logs**:
```bash
# Find which Claude session ran a particular phase:
# 1. Check adw_state.json → adw_id
# 2. Check agents/{adw_id}/sdlc_planner/raw_output.jsonl → session_id (first message)
# 3. Read logs/{session_id}/chat.json for full details
```

## Monitoring Workflows

### Real-Time Monitoring

**Watch state file**:
```bash
watch -n 1 'cat agents/a1b2c3d4/adw_state.json | jq .all_adws'

# Watches `all_adws` list update as phases complete
# Output: ["adw_plan_iso"]  →  ["adw_plan_iso", "adw_build_iso"]  →  ...
```

**Tail logs**:
```bash
# Watch Claude Code tool calls in real-time
tail -f logs/*/pre_tool_use.json | python -m json.tool

# Watch ADW agent logs
tail -f agents/*/*/execution.log
```

**GitHub issue comments**:
```bash
# Open the issue in browser
gh issue view 123 --web

# Or watch comments
while true; do
    gh issue view 123 --json comments --jq '.comments[-1]'
    sleep 5
done
```

### Post-Mortem Analysis

**Summary of a run**:
```bash
adw_id="a1b2c3d4"

echo "=== State ==="
jq . agents/$adw_id/adw_state.json

echo "=== Phases Completed ==="
jq .all_adws agents/$adw_id/adw_state.json

echo "=== Plan File ==="
cat $(jq -r .plan_file agents/$adw_id/adw_state.json) | head -30

echo "=== Test Results ==="
grep -i "test" agents/$adw_id/*/execution.log | tail -20
```

**Failure analysis**:
```bash
# Find the first error
grep -i "error\|failed\|abort" agents/$adw_id/*/execution.log

# Get full context around error
grep -i -B5 -A5 "error" agents/$adw_id/*/execution.log | head -50

# Check raw Claude output for error details
jq '.error' agents/$adw_id/*/raw_output.jsonl
```

## Correlating Across Directories

When debugging a workflow, you often need to jump between directories. Here's how they connect:

### Finding What Happened in a Workflow

**Starting point**: You have an issue number (e.g., #1)

```bash
# 1. Find the ADW ID
ls agents/
# Output: b5facb99, 3f0ecb3a, ...

# 2. Check the state
cat agents/b5facb99/adw_state.json | grep issue_number
# Output: "issue_number": "1"

# 3. See what phases ran
cat agents/b5facb99/adw_state.json | grep all_adws
# Output: "all_adws": ["adw_plan_iso", "adw_build_iso"]

# 4. Check the plan file
cat agents/b5facb99/adw_state.json | grep plan_file
# Output: "plan_file": "specs/issue-1-adw-b5facb99-sdlc_planner-increase-drop-zone-area.md"

# 5. Look at the actual plan
cat trees/b5facb99/specs/issue-1-adw-b5facb99-*.md | head -50

# 6. See what code changed
cd trees/b5facb99
git diff origin/main --stat

# 7. Check Claude's planning response
cat agents/b5facb99/sdlc_planner/raw_output.jsonl | head -20
```

### Finding Claude Code Session for a Phase

**Given**: ADW ID (b5facb99), Phase (sdlc_planner)

```bash
# 1. Check the agent output
ls agents/b5facb99/sdlc_planner/
# raw_output.jsonl (JSONL from Claude Code)
# raw_output.json (clean JSON)
# prompts/feature.txt (what was asked)

# 2. Extract the session ID from the JSONL
head -1 agents/b5facb99/sdlc_planner/raw_output.jsonl | grep -o '"session_id":"[^"]*' | cut -d'"' -f4
# Output: 1f175484-3496-487a-8719-601dff344eb0

# 3. Read that Claude Code session
cat logs/1f175484-3496-487a-8719-601dff344eb0/chat.json | head -100

# 4. Check what tools Claude called
cat logs/1f175484-3496-487a-8719-601dff344eb0/pre_tool_use.json | grep -o '"tool_name":"[^"]*' | head -20
```

### What Gets Logged Where

| Event | Where it's logged |
|-------|-------------------|
| User types a message | `logs/{session_id}/user_prompt_submit.json` |
| Claude Code calls a tool (Read, Write, Bash) | `logs/{session_id}/pre_tool_use.json` |
| Tool completes | `logs/{session_id}/post_tool_use.json` |
| Claude Code session ends | `logs/{session_id}/stop.json` |
| ADW phase starts | `agents/{adw_id}/{phase}/execution.log` |
| ADW phase calls Claude | `agents/{adw_id}/{agent_name}/raw_output.jsonl` |
| ADW state updated | `agents/{adw_id}/adw_state.json` |
| Code changes made | `trees/{adw_id}` (git tracked) |

## Debugging Failures

### Common Issues

#### Issue: "Plan file not created"

```bash
# Check if planner ran
ls agents/{adw_id}/sdlc_planner/

# If raw_output.jsonl exists, Claude ran
# If it's missing, planner was never invoked

# Check the execution log
cat agents/{adw_id}/sdlc_planner/execution.log | tail -20

# Check Claude's output
cat agents/{adw_id}/sdlc_planner/raw_output.jsonl | jq '.error'
```

**Solution**:
- Planner timeout? Try `/health_check` to verify Claude API
- Wrong working directory? Check that worktree exists
- State corrupted? Regenerate with new adw_id

#### Issue: "Worktree not found"

```bash
# List worktrees
git worktree list

# Check if expected one exists
git worktree list | grep {adw_id}

# If missing, rebuild from state
worktree_path=$(jq -r .worktree_path agents/{adw_id}/adw_state.json)
ls -la "$worktree_path"
```

**Solution**:
- Recreate worktree: `git worktree add -b {branch} {path} origin/main`
- Or regenerate entire workflow with new adw_id

#### Issue: "Port already in use"

```bash
# Check which process is using the port
lsof -i :9100
# Output: python  12345  user  4u  IPv4  0x...

# Kill the process
kill -9 12345

# Or get ADW to pick next available port (automatic)
```

#### Issue: "Review shows blockers but can't auto-fix"

```bash
# Check review output
cat agents/{adw_id}/reviewer/execution.log | grep -i "blocker"

# See the actual review result
jq '.review_issues[] | select(.severity=="blocker")' agents/{adw_id}/reviewer/raw_output.jsonl

# If patch loop failed, check patch logs
ls agents/{adw_id}/patch.*/
```

**Solution**:
- Manual fix: Use `/in_loop_review` to let engineer fix
- Or increase `max_patch_attempts` in `adw_review_iso.py`

### Debugging with Claude Code

Run Claude Code interactively to understand what's happening:

```bash
claude -p "Read agents/{adw_id}/sdlc_planner/raw_output.jsonl and explain what went wrong"
```

Or debug a specific command:

```bash
cd trees/{adw_id}
claude -p "/review {adw_id} specs/{spec_file}"
```

## Performance Monitoring

### KPI Tracking

ADW tracks its own performance in `app_docs/agentic_kpis.md`:

```bash
cat app_docs/agentic_kpis.md

# Output:
# | Metric | Value |
# |--------|-------|
# | Current Streak | 3 |
# | Longest Streak | 5 |
# | Total Plan Size | 156 lines |
# | Total Diff | 1,243 added / 87 removed / 23 files |
# | Average Presence | 1.1 (mostly first-try) |
```

**Metrics explain**:
- **Streak**: Consecutive successful runs
- **Plan Size**: Sum of all spec file line counts
- **Diff**: Total code changes across all runs
- **Presence**: How many attempts per issue (1.0 = first try)

### Timing Metrics

Claude Code sessions are timestamped:

```bash
# Measure phase duration
start=$(jq -r '.[] | .timestamp' agents/{adw_id}/sdlc_planner/raw_output.jsonl | head -1)
end=$(jq -r '.[] | .timestamp' agents/{adw_id}/sdlc_implementor/raw_output.jsonl | tail -1)

echo "Plan phase: $start to $end"
```

**Typical timings**:
- Planning: 30-60 seconds
- Building: 20-40 seconds
- Testing: 10-30 seconds
- Review: 30-120 seconds (depends on Playwright)
- Documentation: 10-20 seconds
- **Total SDLC**: 2-5 minutes

### Cost Tracking

Monitor Claude API usage via logs:

```bash
# Count tool uses per model
grep '"model"' agents/*/*/raw_output.jsonl | sort | uniq -c

# Estimate cost:
# haiku: $0.80 per 1M input tokens
# sonnet: $3 per 1M input tokens
# opus: $15 per 1M input tokens
```

## Worktree Management

Worktrees are isolated git copies where each ADW workflow runs. They live in `trees/{adw_id}/` and are ~327 MB total for 2 active worktrees.

### What's in a Worktree

Each worktree is a **complete copy** of the repo with:
- Own git branch (e.g., `feature-issue-1-adw-b5facb99-...`)
- Own `.env` file (copied from main repo)
- Own `.ports.env` file (with allocated backend/frontend ports)
- Own `.mcp.json` with absolute paths
- Own `app/server/database.db` (isolated SQLite)

**Example worktree structure**:
```bash
trees/b5facb99/
├── .env                    ← Copied from main
├── .ports.env              ← Created by /install_worktree
│                             BACKEND_PORT=9112
│                             FRONTEND_PORT=9212
├── .mcp.json               ← Absolute paths to MCP config
├── .git                    ← Symlink to main .git
├── .claude/
├── .gitignore
├── adws/                   ← Full copy of ADW system
├── app/                    ← Full copy of application
│   ├── server/
│   │   └── database.db     ← Isolated test database
│   └── client/
├── app_docs/               ← Generated docs from other runs
├── specs/                  ← Plan files from other runs
└── ai_docs/
```

**Important**: Each worktree is a **complete repository**, not a partial checkout. It's using git worktree, which gives each one:
- Its own branch (checked out)
- Its own working directory
- Shared `.git` metadata with main repo
- Isolated ports so multiple can run simultaneously

### List All Worktrees

```bash
git worktree list

# Output:
# /path/to/repo       (bare)
# /path/to/repo/trees/b5facb99   (detached)
# /path/to/repo/trees/3f0ecb3a   (detached)
```

**Current state**: 2 active worktrees (b5facb99 and 3f0ecb3a), totaling 327 MB

### Inspect a Worktree

```bash
worktree_path=$(jq -r .worktree_path agents/{adw_id}/adw_state.json)

# Check status
cd "$worktree_path"
git status

# Check branch
git branch

# Check ports
cat .ports.env

# Check what was changed
git diff origin/main --stat
```

### Clean Up Abandoned Worktrees

```bash
# Remove worktree and branch
git worktree remove --force trees/{adw_id}

# Prune stale worktrees
git worktree prune

# Remove all trees directory if empty
rm -rf trees/ 2>/dev/null || true
```

### Diagnose Worktree Issues

```bash
# Worktree locked
git worktree list --verbose
# If "locked", unlock:
git worktree unlock trees/{adw_id}

# Stale branch
cd trees/{adw_id}
git fetch origin
git rebase origin/main  # Or reset if you don't care about changes

# Disk space issues
du -sh trees/*/
# Remove largest ones if needed
```

## Database Management

### Reset Database

```bash
sh ./scripts/reset_db.sh

# Creates fresh SQLite database
# Resets schema
# Loads seed data (if any)
```

### Inspect Database

```bash
# SQLite CLI
sqlite3 app/server/database.db

# List tables
.tables

# Query data
SELECT * FROM queries LIMIT 5;

# Exit
.quit
```

### Database per Worktree

Each worktree gets its own database copy:

```bash
# Main repo
app/server/database.db

# Worktree 1
trees/a1b2c3d4/app/server/database.db

# Worktree 2
trees/490eb6b5/app/server/database.db
```

This isolation prevents test data from one worktree affecting another.

## Port Management

### Check Port Usage

```bash
# Which process is using port 9100?
lsof -i :9100
# Output: python  12345  user  4u  IPv4  0x...

# Kill it
kill -9 12345
```

### Force Port Cleanup

```bash
# Find all ADW processes
ps aux | grep "adw_.*_iso.py"

# Kill all
killall python

# Check ports are free
lsof -i :9100 9101 9102 9103  # Should be empty
```

### Port Allocation Check

```bash
# View current allocations
for adw_id in $(ls agents/); do
    echo -n "$adw_id: "
    grep "BACKEND_PORT\|FRONTEND_PORT" agents/$adw_id/.ports.env 2>/dev/null || echo "no ports"
done
```

## Screenshot Management

### Locate Screenshots

**Local screenshots** (default):
```bash
ls agents/{adw_id}/reviewer/review_img/
# export_button_1.png
# query_results_1.png
# ...
```

**Cloud screenshots** (if R2 configured):
```bash
# Check R2 credentials
grep CLOUDFLARE logs/*/user_prompt_submit.json

# URLs will be at: tac-public-imgs.iddagents.com/adw/{adw_id}/...
```

### Clean Up Screenshots

```bash
# Remove old screenshots
rm -rf agents/old_adw_id/reviewer/review_img/*

# Reduce disk usage
du -sh agents/*/reviewer/review_img/ | sort -rh | head -10
```

## Maintenance Tasks

### Weekly Cleanup

```bash
#!/bin/bash
# Weekly ADW cleanup

# Remove old agent logs (>7 days)
find agents -type d -mtime +7 -exec rm -rf {} \;

# Remove old session logs (>7 days)
find logs -type d -mtime +7 -exec rm -rf {} \;

# Clean up old worktrees (>7 days, no active workflow)
git worktree list | tail -n +2 | while read path; do
    modified=$(stat -f %Sm -t '%s' "$path" 2>/dev/null || echo 0)
    age=$(( $(date +%s) - modified ))
    if [ $age -gt 604800 ]; then  # 7 days in seconds
        echo "Removing stale worktree: $path"
        git worktree remove --force "$path"
    fi
done

git worktree prune
```

### Monthly Audit

```bash
# Summary of all runs
echo "=== ADW Run Summary (This Month) ==="
cat app_docs/agentic_kpis.md

# Check for stuck workflows
git worktree list | tail -n +2

# Verify no orphaned branches
git fetch origin
git branch -v | grep gone

# Clean up succeeded branches
git branch -d <branch-name>
```

## Escalation & Support

### When Things Go Wrong

1. **Check logs** — `logs/` and `agents/` directories
2. **Check GitHub issue** — comments from `[ADW-AGENTS]` bot
3. **Check state file** — `agents/{adw_id}/adw_state.json`
4. **Check worktree** — `git worktree list` and `cd trees/{adw_id}`
5. **Manual intervention** — use `/in_loop_review` for engineer review

### If Workflow is Stuck

```bash
# Kill the Python process
ps aux | grep adw_
kill -9 <PID>

# Or use cleanup
/cleanup_worktrees specific {adw_id}
git worktree remove --force trees/{adw_id}

# Inspect state, then regenerate if needed
cat agents/{adw_id}/adw_state.json

# Can delete and retry with new adw_id
rm -rf agents/{adw_id}
```

## Next Steps

- **Extending**: Read `08-extending.md` to add custom functionality
- **Reference**: Review `04-slash-commands.md` for all available commands

### Port Configuration Files

Each worktree has a `.ports.env` file with its allocated ports:

```bash
# View .ports.env in a worktree
cat trees/b5facb99/.ports.env
# Output:
# BACKEND_PORT=9112
# FRONTEND_PORT=9212
# VITE_BACKEND_URL=http://localhost:9112

# View port allocations across all worktrees
for adw_id in $(ls trees/); do
    echo -n "$adw_id: "
    cat "trees/$adw_id/.ports.env" 2>/dev/null || echo "no ports"
done
```

**Why separate `.ports.env`?**
- Each phase script runs in the worktree context
- When `/prepare_app` runs, it sources `.ports.env` to know which ports to use
- This allows multiple worktrees to run simultaneously without port conflicts
- The ports are deterministically assigned based on ADW ID, but fallback to scanning if in use
