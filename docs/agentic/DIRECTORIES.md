# ADW Directory Structure & Organization

Complete guide to the `agents/`, `logs/`, and `trees/` directories.

## Quick Visual: How They Work Together

```
GitHub Issue #1
    ↓
trigger_webhook.py
    ↓
adw_plan_iso.py starts
    ├─ Creates: agents/b5facb99/adw_state.json
    ├─ Creates: trees/b5facb99/ (git worktree)
    ├─ Runs Claude Code (records in logs/{session_id}/)
    ├─ Stores: agents/b5facb99/sdlc_planner/raw_output.jsonl
    └─ Creates: trees/b5facb99/specs/issue-1-adw-b5facb99-*.md
         ↓
      (state persists in agents/b5facb99/adw_state.json)
         ↓
adw_build_iso.py continues
    ├─ Reads: agents/b5facb99/adw_state.json
    ├─ Reads: trees/b5facb99/specs/...md
    ├─ Modifies code in: trees/b5facb99/
    ├─ Stores: agents/b5facb99/sdlc_implementor/raw_output.jsonl
    └─ Commits in: trees/b5facb99/ (git)
         ↓
      (state remains in agents/b5facb99/)
         ↓
adw_test_iso.py, adw_review_iso.py, adw_document_iso.py
    └─ (same pattern: read state, work in trees/, log to agents/)
         ↓
Final cleanup
    ├─ Keep: agents/b5facb99/ (archive later)
    ├─ Keep: logs/{session_id}/ (archive/rotate)
    └─ Remove: trees/b5facb99/ (git worktree remove)
```

## `agents/` — Persistent Workflow State

**Location**: `agents/` at project root
**Size**: ~2.1 MB (100+ ADW runs)
**Lifespan**: Forever (archive as needed)
**Accessed by**: All phase scripts, trigger scripts

### Directory Structure

```
agents/
├── b5facb99/                       ← ADW ID 1 (first workflow)
│   ├── adw_state.json              ← THE KEY FILE (read/write by all phases)
│   ├── adw_plan_iso/
│   │   └── execution.log
│   ├── adw_build_iso/
│   │   └── execution.log
│   ├── sdlc_planner/               ← Planning agent output
│   │   ├── raw_output.jsonl        ← Claude's streaming response (JSONL)
│   │   ├── raw_output.json         ← Converted to clean JSON
│   │   └── prompts/
│   │       └── feature.txt         ← The prompt that was sent
│   ├── sdlc_implementor/           ← Implementation agent output
│   │   ├── raw_output.jsonl
│   │   ├── raw_output.json
│   │   └── prompts/
│   │       └── implement.txt
│   ├── issue_classifier/
│   │   ├── raw_output.jsonl
│   │   ├── raw_output.json
│   │   └── prompts/
│   │       └── classify_issue.txt
│   ├── branch_generator/
│   │   ├── raw_output.jsonl
│   │   └── prompts/
│   │       └── generate_branch_name.txt
│   ├── pr_creator/
│   │   ├── raw_output.jsonl
│   │   └── prompts/
│   │       └── pull_request.txt
│   └── [other agents as needed]
│
├── 3f0ecb3a/                       ← ADW ID 2 (second workflow)
│   ├── adw_state.json
│   └── [same structure as above]
│
└── [more ADW IDs...]
```

### `adw_state.json` Format

```json
{
  "adw_id": "b5facb99",
  "issue_number": "1",
  "branch_name": "feature-issue-1-adw-b5facb99-increase-drop-zone-area",
  "plan_file": "specs/issue-1-adw-b5facb99-sdlc_planner-increase-drop-zone-area.md",
  "issue_class": "/feature",
  "worktree_path": "/Users/pzrinscak/dev/idd/tac-7/trees/b5facb99",
  "backend_port": 9112,
  "frontend_port": 9212,
  "model_set": "base",
  "all_adws": ["adw_plan_iso", "adw_build_iso"]
}
```

**Key fields**:
- **adw_id** — Unique 8-char identifier for this workflow
- **all_adws** — Which phases have run (["adw_plan_iso"] after plan, ["adw_plan_iso", "adw_build_iso"] after build, etc.)
- **plan_file** — Path to the implementation spec (created by planner, used by implementor)
- **worktree_path** — Absolute path to the isolated git worktree
- **backend_port/frontend_port** — Allocated ports for this workflow's app instance

### Agent Output Files

**raw_output.jsonl** (JSONL = newline-delimited JSON):
```
{"type": "event", "data": {...}}
{"type": "message", "role": "assistant", "content": "..."}
{"type": "tool_use", "name": "Read", ...}
...
```
This is Claude Code's streaming output, preserved as-is.

**raw_output.json** (clean JSON):
Same content as .jsonl, but converted to a single JSON array for easier reading.

**prompts/{command}.txt**:
The actual prompt text that was sent to Claude, for debugging.

**execution.log**:
Phase script's own logs (DEBUG level), not from Claude.

### When to Check agents/

- **Troubleshooting a phase** → Read `agents/{adw_id}/{phase}/execution.log`
- **Understanding Claude's reasoning** → Read `agents/{adw_id}/{agent_name}/raw_output.jsonl`
- **Seeing what prompts were sent** → Read `agents/{adw_id}/{agent_name}/prompts/*.txt`
- **Checking workflow progress** → Read `agents/{adw_id}/adw_state.json` → `all_adws` field
- **Finding the plan** → Read `agents/{adw_id}/adw_state.json` → `plan_file` field, then read that file from `trees/`

## `logs/` — Claude Code Session Telemetry

**Location**: `logs/` at project root
**Size**: ~6.9 MB (25+ sessions)
**Lifespan**: Keep for debugging, rotate/archive monthly
**Accessed by**: Debugging, auditing

### Directory Structure

```
logs/
├── 1f175484-3496-487a-8719-601dff344eb0/    ← Session UUID 1
│   ├── user_prompt_submit.json               ← Every user message (JSONL)
│   ├── pre_tool_use.json                     ← Every tool call before execution (JSONL)
│   ├── post_tool_use.json                    ← Every tool result (JSONL)
│   ├── chat.json                             ← Full conversation (converted from JSONL)
│   ├── stop.json                             ← Session end event
│   └── notification.json                     ← Permission prompts (JSONL)
│
├── 41830f2a-8522-4dba-ad1c-8769fdf42e11/    ← Session UUID 2
│   └── [same structure as above]
│
└── [more session UUIDs...]
```

### pre_tool_use.json Format

```json
[
  {
    "session_id": "1f175484-...",
    "transcript_path": "/Users/.../1f175484....jsonl",
    "cwd": "/Users/pzrinscak/dev/idd/tac-7",
    "permission_mode": "default",
    "hook_event_name": "PreToolUse",
    "tool_name": "Read",
    "tool_input": {
      "file_path": "/Users/pzrinscak/dev/idd/tac-7/specs/issue-1-*.md"
    },
    "tool_use_id": "toolu_01Mkdw4Tys8UwYmUySw1BfPR"
  },
  ...
]
```

**Key fields**:
- **tool_name** — Which tool was called (Read, Write, Bash, Glob, Grep, etc.)
- **tool_input** — Arguments passed to the tool
- **cwd** — Working directory where the tool ran
- **hook_event_name** — Always "PreToolUse" (this is what fires the hook)

### stop.json Format

```json
{
  "session_id": "1f175484-3496-487a-8719-601dff344eb0",
  "timestamp": "2026-03-24T23:49:00.123Z",
  "last_assistant_message": "I've completed the analysis...",
  "transcript_path": "..."
}
```

### chat.json Format

Full conversation transcript (converted from JSONL at session end):

```json
[
  {"role": "user", "content": "Tell me about this system"},
  {"role": "assistant", "content": "...response..."},
  {"role": "user", "content": "What about this file?", "tool_use_id": "..."},
  {"role": "tool", "tool_use_id": "...", "content": "file contents..."},
  ...
]
```

### When to Check logs/

- **Debugging tool execution** → Read `logs/{session_id}/pre_tool_use.json` (what tools were called)
- **Seeing tool results** → Read `logs/{session_id}/post_tool_use.json`
- **Understanding security block** → Read `logs/{session_id}/pre_tool_use.json` → look for missing result (blocked at exit code 2)
- **Reviewing full conversation** → Read `logs/{session_id}/chat.json`
- **Finding a specific session** → `ls -lt logs/` to find by date, or grep across all

## `trees/` — Isolated Git Worktrees

**Location**: `trees/` at project root
**Size**: ~327 MB (2 active worktrees)
**Lifespan**: Until workflow complete, then `git worktree remove`
**Accessed by**: Phase scripts (via `working_dir` parameter)

### Directory Structure

```
trees/
├── b5facb99/                       ← Worktree 1 (ADW ID)
│   ├── .git                        ← Symlink to main repo's .git
│   ├── .env                        ← Copied from main repo
│   ├── .ports.env                  ← Created by /install_worktree
│   │                                  BACKEND_PORT=9112
│   │                                  FRONTEND_PORT=9212
│   ├── .mcp.json                   ← Updated with absolute paths
│   ├── .claude/
│   ├── app/                        ← Complete app directory
│   │   ├── server/
│   │   │   ├── main.py
│   │   │   ├── tests/
│   │   │   └── database.db         ← Isolated test database
│   │   └── client/
│   ├── adws/                       ← Complete ADW system
│   ├── specs/                      ← Plan files (symlink to main? or copied?)
│   ├── app_docs/                   ← Generated docs
│   └── [all other repo files]
│
├── 3f0ecb3a/                       ← Worktree 2 (ADW ID)
│   └── [same structure as above]
│
└── [more worktrees as needed]
```

### What Makes a Worktree Different?

Each worktree:
- **Own branch**: Checked out to branch name from `adw_state.json` (e.g., `feature-issue-1-adw-b5facb99-...`)
- **Own working directory**: `trees/{adw_id}/`
- **Shared .git**: Symlinks to main repo's `.git` (no duplication of metadata)
- **Own ports**: `.ports.env` with BACKEND_PORT and FRONTEND_PORT (allows parallel execution)
- **Own database**: `app/server/database.db` (isolated test data)
- **Own .env**: Copy of main repo's `.env` (secrets isolated per worktree)

### Example: What Happens During Phases

**Planning phase** (`adw_plan_iso.py`):
```bash
cd trees/b5facb99
# Runs /install_worktree
# → Creates .ports.env, updates .mcp.json paths
# Runs /feature
# → Claude creates specs/issue-1-adw-b5facb99-*.md IN THE WORKTREE
# Runs /commit
# → git add/commit IN THE WORKTREE
git status
# → Shows modified specs/
git log --oneline -1
# → Shows commit from planner agent
```

**Implementation phase** (`adw_build_iso.py`):
```bash
cd trees/b5facb99
# Loads spec from worktree: specs/issue-1-adw-b5facb99-*.md
# Runs /implement
# → Claude modifies app/client, app/server, etc. IN THE WORKTREE
# Runs /commit
# → git add/commit IN THE WORKTREE
git diff origin/main --stat
# → Shows all code changes (not on disk until after commit)
```

### When to Check trees/

- **Inspecting actual code changes** → `cd trees/{adw_id}` and `git diff origin/main`
- **Debugging a failing test** → `cd trees/{adw_id}` and run tests locally
- **Seeing what was implemented** → `cd trees/{adw_id}` and read modified files
- **Checking .ports.env** → `cat trees/{adw_id}/.ports.env`
- **Reviewing git history** → `cd trees/{adw_id}` and `git log --oneline`

## Cleanup & Rotation

### agents/ — Keep Forever (Archive as Needed)

```bash
# Keep everything for now
# As needed, archive old ones:
tar -czf agents-backup-2026-03-01.tar.gz agents/old_adw_id
rm -rf agents/old_adw_id
```

### logs/ — Rotate Monthly

```bash
# Monthly rotation:
tar -czf logs-backup-2026-02.tar.gz logs/
rm -rf logs/*

# Or selectively:
find logs/ -type d -mtime +30 -exec tar -czf logs-{}.tar.gz {} \; -delete
```

### trees/ — Clean Up After Workflow Complete

```bash
# After adw_sdlc_iso completes
git worktree remove --force trees/b5facb99
git worktree prune

# Or use the cleanup command
/cleanup_worktrees specific b5facb99

# Verify cleaned up
git worktree list  # Should not include trees/b5facb99 anymore
```

## Summary: Which Directory When?

| Question | Look in |
|----------|----------|
| Where is the workflow state? | `agents/{adw_id}/adw_state.json` |
| What phases have run? | `agents/{adw_id}/adw_state.json` → `all_adws` |
| What was the implementation plan? | `trees/{adw_id}/specs/...md` (path from adw_state.json) |
| What code changes were made? | `trees/{adw_id}` (git diff) |
| How long did a phase take? | `agents/{adw_id}/{phase}/execution.log` (timestamps) |
| What did Claude output? | `agents/{adw_id}/{agent_name}/raw_output.jsonl` |
| What tools were called? | `logs/{session_id}/pre_tool_use.json` |
| Were there security blocks? | `logs/{session_id}/pre_tool_use.json` (check for missing results) |
| What are the app ports? | `trees/{adw_id}/.ports.env` |
| Is a worktree still running? | `git worktree list` |

## Examples

### Example 1: Debug Why Plan Phase Failed

```bash
# Check state
cat agents/b5facb99/adw_state.json | jq .

# Check if planner ran
ls agents/b5facb99/sdlc_planner/

# Read planner's execution log
tail -50 agents/b5facb99/adw_plan_iso/execution.log

# Read what Claude actually said
cat agents/b5facb99/sdlc_planner/raw_output.jsonl | head -30

# Read the prompt that was sent
cat agents/b5facb99/sdlc_planner/prompts/feature.txt
```

### Example 2: Understand Code Changes in Build Phase

```bash
# Go to worktree
cd trees/b5facb99

# See what files changed
git diff origin/main --stat

# See specific changes
git diff origin/main -- app/client/src/components/Upload.tsx | head -50

# See the commit that implemented it
git log --oneline -1

# Read the commit message
git log -1 --format="%B"
```

### Example 3: Find Claude Code Session for a Phase

```bash
# Get session ID from JSONL
head -1 agents/b5facb99/sdlc_planner/raw_output.jsonl | jq -r '.session_id'

# Find logs for that session
cat logs/[that-session-id]/chat.json | head -100

# See what tools were called
cat logs/[that-session-id]/pre_tool_use.json | jq '.[] | .tool_name' | sort | uniq -c
```

## Size Metrics

**Current state** (as of 2026-03-25):
- `agents/` — 2.1 MB (18+ ADW IDs with partial/complete runs)
- `logs/` — 6.9 MB (25+ Claude Code sessions)
- `trees/` — 327 MB (2 active worktrees)

**Growth rate**:
- Per ADW run: ~100 KB in agents/, 200 KB in logs/, 160 MB in trees/
- After cleanup (trees removed): ~300 KB total
- Archive recommendation: Archive logs/ monthly, agents/ yearly
