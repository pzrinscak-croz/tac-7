# ADW Agentic Layer — Claude Code Configuration

This document explains how Claude Code is configured for the ADW system: permissions, hooks, and MCP servers.

## Settings Overview

Claude Code is configured via two files:

1. **`.claude/settings.json`** — Global project settings (permissions, hooks)
2. **`.claude/settings.local.json`** — Local overrides (MCP servers, model selection)

## `.claude/settings.json` — Permissions & Hooks

### Permissions

Permissions are whitelists/blacklists of what Claude can do with the Bash tool.

#### Allow List (Whitelist)

These bash commands are permitted:

```json
"allow": [
  "Bash(mkdir:*)",
  "Bash(uv:*)",
  "Bash(find:*)",
  "Bash(mv:*)",
  "Bash(grep:*)",
  "Bash(npm:*)",
  "Bash(ls:*)",
  "Bash(cp:*)",
  "Write",
  "Bash(./scripts/copy_dot_env.sh:*)",
  "Bash(chmod:*)",
  "Bash(touch:*)"
]
```

**Why each command**:
- `mkdir` — create directories for worktrees, logs, agents
- `uv` — run Python scripts and install packages
- `find` — search files for debugging
- `mv` — move/rename files
- `grep` — search file contents
- `npm` — manage JavaScript packages
- `ls` — list directories
- `cp` — copy files (especially for .env files)
- `Write` — write to files (handled by a dedicated tool, not bash)
- `./scripts/copy_dot_env.sh` — safely copy .env files
- `chmod` — change file permissions
- `touch` — create files

#### Deny List (Blacklist)

These commands are **explicitly blocked** and cannot be overridden:

```json
"deny": [
  "Bash(git push --force:*)",
  "Bash(git push -f:*)",
  "Bash(rm -rf:*)"
]
```

**Why**:
- `git push --force` — prevents overwriting upstream history
- `git push -f` — same (short form)
- `rm -rf` — prevents accidental repo destruction

### Hooks

Hooks are Python scripts that fire on lifecycle events. They're invoked via `uv run` so they have full Python runtime.

```json
"hooks": [
  {
    "name": "PreToolUse",
    "script": "pre_tool_use.py",
    "matcher": {}
  },
  {
    "name": "PostToolUse",
    "script": "post_tool_use.py",
    "matcher": {}
  },
  {
    "name": "Notification",
    "script": "notification.py",
    "args": ["--notify"],
    "matcher": {}
  },
  {
    "name": "Stop",
    "script": "stop.py",
    "args": ["--chat"],
    "matcher": {}
  },
  {
    "name": "SubagentStop",
    "script": "subagent_stop.py",
    "matcher": {}
  },
  {
    "name": "PreCompact",
    "script": "pre_compact.py",
    "matcher": {}
  },
  {
    "name": "UserPromptSubmit",
    "script": "user_prompt_submit.py",
    "args": ["--log-only"],
    "matcher": {}
  }
]
```

## Hooks Deep Dive

All hooks are located in `.claude/hooks/` and handle different events. They read JSON from stdin (provided by Claude Code) and write logs to `logs/{session_id}/`.

### `pre_tool_use.py` — Security Guardian

**Event**: Before every tool call
**Critical**: YES — can block tool execution with exit code 2

This hook is your security layer. It performs two critical checks:

#### Check 1: `.env` File Protection

Blocks any attempt to read or write `.env` files:

```python
def check_env_file_access(tool_name, tool_input):
    if tool_name in ["Read", "Edit", "Write", "Bash"]:
        # Extract file paths from tool input
        paths = extract_file_paths(tool_input)

        for path in paths:
            if ".env" in path and not path.endswith(".env.sample"):
                # BLOCK: .env access is forbidden
                print("Error: .env file access is not permitted", file=sys.stderr)
                sys.exit(2)  # Exit code 2 blocks the tool call
```

**Why**: `.env` files contain `ANTHROPIC_API_KEY` and `GITHUB_PAT`. Preventing access prevents credential leakage.

#### Check 2: Dangerous `rm` Command Protection

Blocks any recursive delete pattern:

```python
DANGEROUS_PATTERNS = [
    r"rm\s+-rf",           # rm -rf
    r"rm\s+-fr",           # rm -fr
    r"rm\s+--recursive\s+--force",  # long form
    r"rm\s+-r\s+/",        # rm -r /
    r"rm\s+-r\s+~",        # rm -r ~
    r"rm\s+-r\s+.*\*",     # rm -r with wildcards
]

def check_dangerous_rm(bash_command):
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, bash_command):
            # BLOCK: dangerous rm
            print(f"Error: Dangerous rm command blocked: {bash_command}", file=sys.stderr)
            sys.exit(2)
```

**Why**: Prevents accidental destruction of the repo or user files.

#### Logging

After checks pass, logs the tool call:

```python
tool_call_log = {
    "timestamp": datetime.now().isoformat(),
    "session_id": input_json["session_id"],
    "tool_name": tool_name,
    "tool_input": tool_input,
    "cwd": input_json.get("cwd"),
    "permission_mode": input_json.get("permission_mode"),
}

with open(f"logs/{session_id}/pre_tool_use.json", "a") as f:
    f.write(json.dumps(tool_call_log) + "\n")
```

### `post_tool_use.py` — Result Logging

**Event**: After every tool call completes
**Critical**: NO — pure logging, doesn't block

Appends the tool result to `logs/{session_id}/post_tool_use.json`:

```python
tool_result_log = {
    "timestamp": datetime.now().isoformat(),
    "session_id": input_json["session_id"],
    "tool_name": tool_name,
    "success": success,
    "result": result,
    "error": error,
    "duration_ms": duration_ms,
}

with open(f"logs/{session_id}/post_tool_use.json", "a") as f:
    f.write(json.dumps(tool_result_log) + "\n")
```

### `stop.py` — Session Finalizer

**Event**: When a Claude Code session ends (all prompts completed)
**Args**: `--chat` flag enables transcript conversion

Actions:
1. Log the session stop event (when it ended, last assistant message)
2. If `--chat` flag is set, convert the `.jsonl` session transcript to a cleaner `.json` format

```python
# Input from Claude Code
input_json = json.loads(sys.stdin.read())
session_id = input_json["session_id"]
transcript_path = input_json.get("transcript_path")

# Log the stop event
stop_log = {
    "timestamp": datetime.now().isoformat(),
    "session_id": session_id,
    "last_assistant_message": input_json.get("last_assistant_message"),
}

with open(f"logs/{session_id}/stop.json", "w") as f:
    json.dump(stop_log, f, indent=2)

# Convert transcript if available
if transcript_path and os.path.exists(transcript_path):
    transcript = []
    with open(transcript_path) as f:
        for line in f:
            transcript.append(json.loads(line))

    with open(f"logs/{session_id}/chat.json", "w") as f:
        json.dump(transcript, f, indent=2)
```

### `subagent_stop.py` — Subagent Session Finalizer

**Event**: When a subagent (spawned by ADW script) ends
**Identical to**: `stop.py` but writes to `subagent_stop.json`

Used when ADW scripts invoke Claude Code as subprocesses. Each subagent session gets its own logs.

### `user_prompt_submit.py` — Prompt Logging & Validation

**Event**: Every time the user submits a message
**Args**: `--log-only` flag enables validation (currently disabled)

Logs every user prompt:

```python
user_prompt_log = {
    "timestamp": datetime.now().isoformat(),
    "session_id": session_id,
    "cwd": input_json.get("cwd"),
    "permission_mode": input_json.get("permission_mode"),
    "prompt": input_json.get("prompt"),
}

with open(f"logs/{session_id}/user_prompt_submit.json", "a") as f:
    f.write(json.dumps(user_prompt_log) + "\n")
```

With `--validate` flag (not enabled), this could block prompts matching a deny list (currently empty placeholder).

### `notification.py` — Notification Telemetry

**Event**: On permission prompts (user is asked to approve a tool), idle alerts, or other notifications
**Args**: `--notify` flag (TTS was previously implemented but removed)

Currently logs notifications to `logs/{session_id}/notification.json`.

### `pre_compact.py` — Context Compaction Telemetry

**Event**: Before Claude Code compacts the context window (when conversation gets very long)
**Critical**: NO — pure logging

Logs context compaction events for performance analysis.

### Hook Utilities

#### `hooks/utils/constants.py`

Shared utility for all hooks:

```python
LOG_BASE_DIR = os.getenv("CLAUDE_HOOKS_LOG_DIR", "logs")

def ensure_session_log_dir(session_id: str) -> Path:
    """Create logs/{session_id}/ if it doesn't exist"""
    log_dir = Path(LOG_BASE_DIR) / session_id
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir

def get_session_log_dir(session_id: str) -> Path:
    """Get the log directory for a session"""
    return Path(LOG_BASE_DIR) / session_id
```

#### `hooks/utils/llm/anth.py` & `hooks/utils/llm/oai.py`

Optional LLM utilities for hooks (used by older implementations for generating completion messages via TTS). Now mostly stubs.

## `.claude/settings.local.json` — MCP Servers

Local settings override global settings. This file enables MCP servers:

```json
{
  "enabledMcpjsonServers": ["playwright"],
  "enableAllProjectMcpServers": true
}
```

**What it does**:
- `enabledMcpjsonServers`: List of MCP servers from `.mcp.json` to enable
- `enableAllProjectMcpServers`: If true, enable all project MCP servers

## `.mcp.json` — MCP Server Configuration

MCP (Model Context Protocol) enables Claude Code to use external tools. ADW uses Playwright for browser automation.

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--isolated",
        "--config",
        "--image-responses",
        "omit",
        "./playwright-mcp-config.json"
      ]
    }
  }
}
```

**Flags**:
- `--isolated`: Each browser session is sandboxed (important for security)
- `--image-responses omit`: Screenshots are saved to disk but not sent back as base64 (cost optimization)
- `./playwright-mcp-config.json`: Playwright config file path

## `playwright-mcp-config.json` — Browser Automation Config

Configures Playwright for the `/review` and `/test_e2e` commands:

```json
{
  "browsers": ["chromium"],
  "headless": true,
  "viewport": {
    "width": 1920,
    "height": 1080
  },
  "recordVideo": {
    "dir": "agents/videos"
  }
}
```

**Settings**:
- `browsers`: Use Chromium (smaller than Firefox/Webkit)
- `headless: true`: No GUI (server environment)
- `viewport`: 1920x1080 standard resolution for consistent screenshots
- `recordVideo`: Optional video recording of browser sessions

### Worktree-Specific Config

When `/install_worktree` runs, it updates the MCP config with absolute paths:

```python
# From .claude/commands/install_worktree.md
# Before: "./playwright-mcp-config.json"
# After: "/absolute/path/to/worktree/playwright-mcp-config.json"
```

**Why**: Worktrees may be at different paths. Absolute paths ensure Playwright works correctly.

## How Hooks Interact During a Workflow

Here's what happens during a single ADW workflow run:

```
User triggers: uv run adws/adw_plan_iso.py 123

├─ Claude Code session starts
│
├─ pre_tool_use.py (every tool call)
│  └─ Checks .env access, dangerous rm, logs to pre_tool_use.json
│
├─ Tool executes
│
├─ post_tool_use.py (immediately after)
│  └─ Logs result to post_tool_use.json
│
├─ user_prompt_submit.py (on user input)
│  └─ Logs prompt to user_prompt_submit.json
│
├─ notification.py (on permission prompts)
│  └─ Logs notifications to notification.json
│
└─ stop.py (session ends)
   └─ Logs stop event, converts transcript to chat.json
```

All logs go to `logs/{session_id}/` which allows debugging and auditing.

## Security Model

The security model has multiple layers:

**Layer 1: Permissions (settings.json)**
- Whitelist of allowed bash commands
- Blacklist of dangerous commands

**Layer 2: Hooks (pre_tool_use.py)**
- Runtime enforcement of .env protection
- Runtime detection of dangerous rm patterns
- Can exit with code 2 to block execution

**Layer 3: Working Directory Isolation**
- Claude runs with `--cwd worktree_path`
- Modifications are scoped to the worktree
- Main branch is never directly modified

**Layer 4: State Validation**
- All state is validated on load via Pydantic
- Invalid state raises an error
- Prevents corruption from propagating

## Debugging Configuration Issues

### Issue: Permission Denied

```
Error: Bash(rm -rf:*) - Permission denied
```

Solution: Check if the command is in the deny list. It's intentionally blocked.

### Issue: MCP Server Not Found

```
Error: Playwright MCP server not found
```

Solution: Verify `.mcp.json` exists and `enabledMcpjsonServers` includes "playwright" in `settings.local.json`.

### Issue: Hook Not Running

```
# Pre-tool hook didn't log anything
```

Solution: Check that the hook script exists at `.claude/hooks/{name}.py` and is executable. Also verify the hook is registered in `settings.json`.

### Issue: .env Access Blocked

```
Error: .env file access is not permitted
```

This is intentional. Use `.env.sample` for documentation or the `copy_dot_env.sh` script for safe copying.

## Next Steps

- **Slash Commands**: Read `04-slash-commands.md` to see how commands are invoked
- **Workflow Scripts**: Read `05-workflow-scripts.md` to see how Claude Code is orchestrated
- **Operations**: Read `07-operations.md` to see how to monitor and debug
