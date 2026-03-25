# ADW Agentic Layer — Core Concepts

This document covers the fundamental building blocks that make the ADW system work. Understanding these concepts is essential to operating and extending the system.

## ADW ID

An **ADW ID** is an 8-character hexadecimal identifier that uniquely represents a single workflow run.

### Format
```
a1b2c3d4
├── 8 hex chars (0-9, a-f)
└── Generated from UUID slice: uuid4().hex[:8]
```

### Examples
- `cc73faf1` — for issue #47 (upload button chore)
- `490eb6b5` — for issue #48 (CSV export feature)
- `4c768184` — for issue #49 (model upgrades)

### Where It's Used
The ADW ID is the namespace for everything related to that workflow run:

| Directory/File | Purpose |
|---|---|
| `trees/{adw_id}/` | Isolated git worktree |
| `agents/{adw_id}/adw_state.json` | Persistent state file |
| `agents/{adw_id}/sdlc_planner/` | Planner agent logs |
| `agents/{adw_id}/sdlc_implementor/` | Implementor agent logs |
| `agents/{adw_id}/reviewer/` | Reviewer agent logs + screenshots |
| `app_docs/feature-{adw_id}-*.md` | Generated docs for this run |

### Why It Matters
- **Traceability**: Search for `a1b2c3d4` in logs/comments/docs to find all artifacts from one workflow
- **Isolation**: Each ADW ID gets its own worktree, ports, state file
- **Parallelism**: Multiple ADW IDs can run simultaneously without conflict

## ADW State

The **ADW State** is a JSON file at `agents/{adw_id}/adw_state.json` that persists across all phases of a workflow. It is the **single source of truth** connecting all phases and is stored in the main repository (not in worktrees) so it's always accessible.

### Schema

```python
@dataclass
class ADWState:
    adw_id: str                    # 8-char hex ID
    issue_number: int              # GitHub issue number (e.g., 123)
    branch_name: str               # Git branch name
    plan_file: str                 # Path to the spec file
    issue_class: str               # "chore" | "bug" | "feature"
    worktree_path: str             # Absolute path to trees/{adw_id}/
    backend_port: int              # Allocated backend port (9100-9114)
    frontend_port: int             # Allocated frontend port (9200-9214)
    model_set: str                 # "base" | "heavy"
    all_adws: list[str]            # Which phases have run
```

### Lifecycle

**Phase 1 — Planning** (`adw_plan_iso.py`):
```python
state.adw_id = "a1b2c3d4"
state.issue_number = 123
state.branch_name = "feat-issue-123-a1b2c3d4-add-feature"
state.plan_file = "specs/issue-123-adw-a1b2c3d4-sdlc_planner-add-feature.md"
state.issue_class = "feature"
state.worktree_path = "/path/to/trees/a1b2c3d4"
state.backend_port = 9100
state.frontend_port = 9200
state.model_set = "base"
state.all_adws = ["adw_plan_iso"]
state.save()  # Write to agents/{adw_id}/adw_state.json
```

**Phase 2 — Building** (`adw_build_iso.py`):
```python
state = ADWState.load("a1b2c3d4")  # Read from agents/{adw_id}/adw_state.json
# All fields from Phase 1 are already populated
state.all_adws.append("adw_build_iso")
state.save()  # Write back
```

**Phase 3–5**: Each phase reads, appends to `all_adws`, saves.

### Passing State Between Subprocesses

Because ADW phases are separate Python scripts run via `subprocess.run()`, they can't share memory. State is passed via files:

```python
# Phase 1 (adw_plan_iso.py)
state = ADWState(adw_id="a1b2c3d4", issue_number=123, ...)
state.save()  # Write to disk

# Phase 2 (adw_build_iso.py) — different process, different memory
state = ADWState.load("a1b2c3d4")  # Read from disk
# Now has all fields from Phase 1
```

### Validation

Every time you load state, it's validated against the Pydantic schema. Invalid state raises a `ValidationError`:

```python
try:
    state = ADWState.load("a1b2c3d4")
except ValidationError as e:
    print(f"State is corrupted: {e}")
```

### Debugging State

```bash
cat agents/a1b2c3d4/adw_state.json | python -m json.tool
```

## Git Worktrees

A **git worktree** is a feature of Git that lets you have multiple working directories from the same repository.

### Why ADW Uses Worktrees

Without worktrees, if two workflows ran concurrently:
- Workflow A checks out branch `feat-123`
- Workflow B checks out branch `feat-456` in the same directory
- Both try to modify files in the same working directory → conflicts, race conditions

With worktrees:
- Workflow A works in `trees/a1b2c3d4/` on branch `feat-123`
- Workflow B works in `trees/4c768184/` on branch `feat-456`
- Completely isolated, no conflicts

### How Worktrees Are Created

In `adw_plan_iso.py`:

```python
from adw_modules.worktree_ops import create_worktree

create_worktree(adw_id="a1b2c3d4", branch_name="feat-issue-123-...", logger=logger)
# Executes: git worktree add -b feat-issue-123-... trees/a1b2c3d4 origin/main
# Result: trees/a1b2c3d4/ contains a complete repo copy on the new branch
```

### Directory Layout

```
tac-7/
├── .git/              ← Main repo metadata
├── app/               ← Main working directory (main branch)
├── adws/
├── specs/
├── agents/
├── logs/
└── trees/             ← Worktree storage
    ├── a1b2c3d4/      ← Worktree 1 (feat-issue-123-...)
    │   ├── .git       ← Symlink to main .git
    │   ├── app/
    │   ├── adws/
    │   └── .ports.env ← Isolated ports
    ├── 4c768184/      ← Worktree 2 (feat-issue-456-...)
    │   ├── .git
    │   ├── app/
    │   ├── .ports.env
    │   └── ...
    └── ...
```

### Working in a Worktree

All ADW scripts that run Claude pass `working_dir=state.worktree_path` to `execute_template()`:

```python
# From adw_build_iso.py
response = execute_template(
    request=AgentTemplateRequest(
        slash_command="/implement",
        arguments=plan_file,
        working_dir=state.worktree_path,  # ← Run /implement in worktree
    )
)
```

Claude Code CLI then runs with `--cwd worktree_path`, so all file changes are isolated.

### Cleanup

```bash
# List all worktrees
git worktree list
# Output:
# /Users/pzrinscak/dev/idd/tac-7       (bare)
# /Users/pzrinscak/dev/idd/tac-7/trees/a1b2c3d4  (detached)

# Remove a worktree
git worktree remove trees/a1b2c3d4

# Force remove if branch is in weird state
git worktree remove --force trees/a1b2c3d4
```

## Port Management

Each worktree needs its own ports for the backend and frontend. ADW allocates ports deterministically with fallback.

### Allocation Algorithm

For an ADW ID like `a1b2c3d4`:

```python
def get_ports_for_adw(adw_id):
    # Convert first 8 hex chars to integer, mod 15 → 0-14
    base = int(adw_id[:8], 36) % 15

    # Two port ranges: 9100-9114 (backend), 9200-9214 (frontend)
    backend_port = 9100 + base
    frontend_port = 9200 + base

    return backend_port, frontend_port

# Examples:
get_ports_for_adw("a1b2c3d4") → (9101, 9201)
get_ports_for_adw("4c768184") → (9107, 9207)
```

### Fallback for Port Conflicts

If the deterministic port is already in use:

```python
def find_next_available_ports(adw_id, max_attempts=15):
    ports = get_ports_for_adw(adw_id)

    # Try ports in sequence, up to max_attempts
    for i in range(max_attempts):
        candidate_backend = ports.backend + i
        candidate_frontend = ports.frontend + i

        if is_port_available(candidate_backend) and is_port_available(candidate_frontend):
            return candidate_backend, candidate_frontend

    raise Exception(f"Could not find available ports after {max_attempts} attempts")
```

### Setting Ports in a Worktree

In `adw_plan_iso.py`:

```python
from adw_modules.worktree_ops import setup_worktree_environment

setup_worktree_environment(
    worktree_path="trees/a1b2c3d4",
    backend_port=9100,
    frontend_port=9200,
    logger=logger
)
# Creates: trees/a1b2c3d4/.ports.env
# Contents: BACKEND_PORT=9100, FRONTEND_PORT=9200, VITE_BACKEND_URL=http://localhost:9100
```

### Using Ports in Claude Commands

When `/prepare_app` or `/start` runs in a worktree, it reads `.ports.env`:

```bash
# Inside a worktree context
source .ports.env
echo $BACKEND_PORT    # Output: 9100
echo $FRONTEND_PORT   # Output: 9200
```

## Model Sets

A **model set** determines which LLM models are used for each task. There are two sets: `"base"` and `"heavy"`.

### Base Model Set

Used for standard workflows. Cheaper, adequate quality:

| Command | Model |
|---------|-------|
| `/classify_issue`, `/generate_branch_name`, `/commit`, `/pull_request` | `haiku` |
| `/feature`, `/bug`, `/chore`, `/implement`, `/patch`, `/document` | `sonnet` |
| `/test`, `/test_e2e`, `/review`, `/classify_adw` | `sonnet` |

**Cost**: Very low. Optimized for deterministic, well-scoped tasks.

### Heavy Model Set

Used when maximum quality is needed. More expensive, better reasoning:

| Command | Model |
|---------|-------|
| `/classify_issue`, `/generate_branch_name`, `/commit`, `/pull_request` | `haiku` |
| `/feature`, `/bug`, `/chore`, `/implement`, `/patch`, `/document` | `opus` |
| `/test`, `/test_e2e`, `/review`, `/classify_adw` | `sonnet` |

**Cost**: Higher. Worth it for complex features, architectural changes.

### How to Choose

In your GitHub issue or comment:

```markdown
# Standard workflow (uses base model set)
Title: "Fix button alignment"
Body: "adw_sdlc_iso"

# Premium workflow (uses heavy model set)
Title: "Redesign entire dashboard"
Body: "adw_sdlc_iso model_set heavy"
```

### Model Assignment Code

From `adw_modules/agent.py`:

```python
SLASH_COMMAND_MODEL_MAP = {
    # Base set
    "base": {
        "classify_issue": "haiku",
        "feature": "sonnet",
        "implement": "sonnet",
        # ... etc
    },
    # Heavy set
    "heavy": {
        "classify_issue": "haiku",
        "feature": "opus",     # ← Upgraded from sonnet
        "implement": "opus",   # ← Upgraded from sonnet
        # ... etc
    }
}

def get_model_for_slash_command(command: str, model_set: str) -> str:
    return SLASH_COMMAND_MODEL_MAP[model_set][command]
```

## Slash Command Vocabulary

A **slash command** is a markdown file in `.claude/commands/` that defines a reusable Claude prompt. When invoked, the command is loaded and parameters are injected.

### How Slash Commands Work

**File**: `.claude/commands/feature.md`
```markdown
# Feature Planning

Create a comprehensive implementation plan for this feature.

## Arguments
- $ARGUMENTS (required): GitHub issue JSON

## Output
Return only the plain-text path to the created spec file. No markdown, no backticks.
```

**Invocation** (from `workflow_ops.py`):
```python
from adw_modules.agent import execute_template

response = execute_template(
    request=AgentTemplateRequest(
        slash_command="/feature",
        arguments='{"title":"Add CSV export","body":"..."}',
        working_dir="trees/a1b2c3d4"
    )
)
# Claude Code loads .claude/commands/feature.md
# Injects the JSON into the prompt
# Runs with model selection from SLASH_COMMAND_MODEL_MAP
# Returns the response
```

### Return Value Convention

**Planning commands** (`/feature`, `/bug`, `/chore`, `/patch`) return **only the plain-text path**:
```
specs/issue-47-adw-cc73faf1-sdlc_planner-update-upload-button.md
```

Not:
```
```specs/issue-47-adw-cc73faf1-sdlc_planner-update-upload-button.md```
```

**Why**: The Python script reads the response and immediately uses it as a file path. Markdown syntax breaks the path parsing.

### All 28 Commands

See `04-slash-commands.md` for the complete reference.

## Structured Outputs with JSON Schema

Some commands use Claude's `--json-schema` flag to enforce structured outputs. Example: `/classify_issue` must return exactly `/bug`, `/feature`, `/chore`, `/patch`, or `0`.

**Command invocation** (from `agent.py`):
```python
claude -p "<prompt>" --model haiku --json-schema <SCHEMA> --output-format stream-json
```

**Schema** (enforced):
```json
{
  "type": "object",
  "properties": {
    "command": {
      "type": "string",
      "enum": ["/bug", "/feature", "/chore", "/patch", "0"]
    }
  },
  "required": ["command"]
}
```

**Response**:
```json
{"command": "/feature"}
```

The Python script can then parse this with certainty:
```python
result = json.loads(response)
issue_class = result["command"]  # Guaranteed to be valid
```

## Complete Example: How It All Works Together

**GitHub Issue #47**:
```
Title: "Update upload button text"
Body: "adw_sdlc_iso model_set heavy"
```

**Step 1: Trigger** (`trigger_webhook.py`):
- Webhook detects `adw_` in body
- Calls `/classify_adw` to extract workflow and model_set
- Spawns `adw_sdlc_iso.py 47` as background subprocess

**Step 2: Planning** (`adw_plan_iso.py 47`):
- Generates ADW ID: `cc73faf1`
- Creates worktree: `trees/cc73faf1/` on branch `chore-issue-47-cc73faf1-update-upload-button`
- Allocates ports: backend=9101, frontend=9201
- Calls `/install_worktree` (sonnet) in worktree
- Calls `/classify_issue` (haiku, JSON schema) → returns `{"command": "/chore"}`
- Calls `/generate_branch_name` (haiku) → returns the branch name
- Calls `/chore` (opus, because model_set=heavy) → creates spec file
- Commits and pushes
- Saves state with all fields populated

**Step 3: Building** (`adw_build_iso.py 47 cc73faf1`):
- Loads state from `agents/cc73faf1/adw_state.json`
- Calls `/implement specs/issue-47-adw-cc73faf1-sdlc_planner-update-upload-button.md` (opus)
- Claude reads the spec and modifies code in the worktree
- Commits and pushes

**Step 4: Testing** (`adw_test_iso.py 47 cc73faf1`):
- Calls `/test` (sonnet) → runs pytest + tsc + build
- All pass ✓

**Step 5: Review** (`adw_review_iso.py 47 cc73faf1`):
- Calls `/prepare_app` (sonnet) → starts app on port 9201
- Calls `/review` (sonnet) → uses Playwright MCP to take 3 screenshots, compares to spec
- All match ✓

**State file** (`agents/cc73faf1/adw_state.json`):
```json
{
  "adw_id": "cc73faf1",
  "issue_number": 47,
  "branch_name": "chore-issue-47-cc73faf1-update-upload-button",
  "plan_file": "specs/issue-47-adw-cc73faf1-sdlc_planner-update-upload-button.md",
  "issue_class": "chore",
  "worktree_path": "/Users/pzrinscak/dev/idd/tac-7/trees/cc73faf1",
  "backend_port": 9101,
  "frontend_port": 9201,
  "model_set": "heavy",
  "all_adws": ["adw_plan_iso", "adw_build_iso", "adw_test_iso", "adw_review_iso"]
}
```

## Next Steps

- **Claude Code Layer**: Read `03-claude-code-layer.md` to understand hooks and command configuration
- **All Commands**: Read `04-slash-commands.md` for reference of all 28 commands
- **Workflow Scripts**: Read `05-workflow-scripts.md` for the ADW phase/pipeline scripts
