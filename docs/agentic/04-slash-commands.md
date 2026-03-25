# ADW Agentic Layer — Slash Commands Reference

All commands are markdown files in `.claude/commands/`. This document lists all 28 commands organized by category.

## Planning Commands

### `/feature` — Feature Planning
**File**: `feature.md`

Creates a comprehensive implementation plan for a new feature.

**Arguments**:
- `$ARGUMENTS`: GitHub issue JSON (required)

**Returns**: Plain-text path to spec file in `specs/`

**Model**: Sonnet (base) or Opus (heavy)

**Flow**:
1. Claude researches the codebase (reads conditional_docs.md, relevant code files)
2. Analyzes the feature request
3. Creates `specs/issue-{N}-adw-{id}-sdlc_planner-{name}.md` with:
   - Feature description
   - User story
   - Problem/solution statements
   - Relevant files to modify
   - 3-phase implementation plan
   - Step-by-step tasks (numbered, explicit)
   - Testing strategy (including E2E test file creation if UI is affected)
   - Acceptance criteria
   - Validation commands
4. Returns only the plain-text file path

**Used by**: `adw_plan_iso.py` (planning phase)

### `/bug` — Bug Fix Planning
**File**: `bug.md`

Same structure as `/feature` but focused on root cause analysis.

**Arguments**:
- `$ARGUMENTS`: GitHub issue JSON (required)

**Returns**: Plain-text path to spec file in `specs/`

**Model**: Sonnet (base) or Opus (heavy)

**Differences from /feature**:
- Emphasizes reproduction steps
- Focuses on minimal, surgical fixes
- Includes root cause analysis section

**Used by**: `adw_plan_iso.py` (planning phase)

### `/chore` — Maintenance Task Planning
**File**: `chore.md`

For maintenance, refactoring, or cleanup tasks.

**Arguments**:
- `$ARGUMENTS`: GitHub issue JSON (required)

**Returns**: Plain-text path to spec file in `specs/`

**Model**: Sonnet (base) or Opus (heavy)

**Simpler than feature/bug**:
- No multi-phase planning
- No acceptance criteria
- Focuses on scope and affected files

**Used by**: `adw_plan_iso.py` (planning phase)

### `/patch` — Targeted Patch Planning
**File**: `patch.md`

Creates a minimal patch plan for review-driven fixes.

**Arguments**:
- `adw_id` (required)
- `review_change_request` (required): Description of what to fix
- `spec_path` (optional): Original spec file
- `agent_name` (optional): Which agent is making the patch
- `issue_screenshots` (optional): Screenshots from the review

**Returns**: Plain-text path to patch spec file in `specs/patch/`

**Model**: Sonnet (base) or Opus (heavy)

**Output format**: `specs/patch/patch-adw-{id}-{name}.md` (minimal, focused plan)

**Used by**: `adw_review_iso.py` (when review finds blockers and loops for patches)

## Implementation Commands

### `/implement` — Code Implementation
**File**: `implement.md`

Reads a spec file and implements the code changes described in it.

**Arguments**:
- `$ARGUMENTS`: Path to spec file (required)

**Returns**: Plain-text summary of changes, `git diff --stat`

**Model**: Sonnet (base) or Opus (heavy)

**Flow**:
1. Claude reads the spec file
2. Analyzes step-by-step tasks
3. Modifies code in the worktree
4. Returns `git diff --stat` showing:
   - Files added
   - Files modified
   - Lines added/removed

**Used by**: `adw_build_iso.py` (build phase)

## Testing Commands

### `/test` — Full Test Suite
**File**: `test.md`

Runs all tests in sequence and returns structured results.

**Arguments**: None

**Returns**: JSON array of test results

**Model**: Sonnet (base and heavy)

**Tests run** (in order):
1. Python syntax check (`python -m py_compile`)
2. Backend linting (`uv run ruff check app/server`)
3. Backend unit tests (`uv run pytest app/server/tests`)
4. TypeScript type check (`bun tsc app/client`)
5. Frontend build (`bun run build -C app/client`)

**Behavior**: Stops on first failure (returns failure immediately)

**Result schema**:
```json
[
  {
    "name": "Python Syntax Check",
    "status": "passed",
    "duration_ms": 150
  },
  {
    "name": "Backend Linting",
    "status": "passed",
    "duration_ms": 320
  },
  {
    "name": "Backend Unit Tests",
    "status": "failed",
    "error": "AssertionError: expected True got False",
    "duration_ms": 1500
  }
]
```

**Used by**: `adw_test_iso.py` (testing phase)

### `/test_e2e` — End-to-End Browser Tests
**File**: `test_e2e.md`

Uses Playwright MCP to run browser automation tests.

**Arguments**:
- `adw_id` (required)
- `agent_name` (required): Which agent is running this
- `e2e_test_file` (required): Path to test file (e.g., `.claude/commands/e2e/test_basic_query.md`)
- `application_url` (optional): App URL (auto-detected from `.ports.env`)

**Returns**: JSON with test results and screenshot paths

**Model**: Sonnet (base and heavy)

**Test file format** (e.g., `test_basic_query.md`):
```markdown
# E2E Test: Basic Query Execution

## User Story
As a user, I can enter a natural language query and see results.

## Test Steps
1. Navigate to http://localhost:5173
2. Enter query "SELECT all users" in the search box
3. Click "Execute" button
4. Verify results table appears
5. Screenshot: results-table.png

## Success Criteria
- Query executes without errors
- Results table displays
- Response time < 5 seconds
```

**Used by**: `adw_test_iso.py` (optional E2E testing)

### `/resolve_failed_test` — Auto-Fix Test Failures
**File**: `resolve_failed_test.md`

Analyzes test failures and makes targeted fixes.

**Arguments**:
- `$ARGUMENTS`: Test failure JSON (required)

**Returns**: JSON with fix result

**Model**: Sonnet (base) or Opus (heavy)

**Flow**:
1. Claude reads the failure JSON
2. Discovers context from `git diff`
3. Reproduces the failure
4. Makes minimal targeted fix
5. Re-runs only the specific test
6. Returns success/failure result

**Used by**: `adw_test_iso.py` (when tests fail)

### `/resolve_failed_e2e_test` — Auto-Fix E2E Failures
**File**: `resolve_failed_e2e_test.md`

Same as `/resolve_failed_test` but for browser test failures.

**Used by**: `adw_test_iso.py` (when E2E tests fail)

## Review Commands

### `/review` — Spec Compliance Review
**File**: `review.md`

Most complex command. Verifies implementation matches spec.

**Arguments**:
- `adw_id` (required)
- `spec_file` (required): Path to the original spec file
- `agent_name` (required): Which agent is reviewing

**Returns**: JSON `ReviewResult` with severity-classified issues

**Model**: Sonnet (base and heavy)

**Flow**:
1. Reads the spec file
2. Runs `git diff origin/main` to see what changed
3. Calls `/prepare_app` to start the running application
4. Uses Playwright MCP to navigate the app
5. Takes 1-5 targeted screenshots of critical user paths
6. Compares implementation against spec requirements
7. Classifies any issues:
   - `skippable`: Nice-to-have improvements (e.g., better spacing)
   - `tech_debt`: Should fix but not blocking (e.g., performance)
   - `blocker`: Must fix (breaks feature or fails spec)
8. Returns structured JSON

**Result schema**:
```json
{
  "success": false,
  "review_summary": "Implementation is mostly correct but has 1 blocking issue",
  "review_issues": [
    {
      "title": "Export button text is incorrect",
      "description": "Spec says 'Download as CSV', but UI shows 'Export CSV'",
      "severity": "blocker",
      "location": "app/client/src/components/ExportButton.tsx:45"
    },
    {
      "title": "Button spacing could be improved",
      "severity": "skippable"
    }
  ],
  "screenshots": [
    {
      "name": "export_button",
      "description": "Export button in the main view",
      "url": "agents/{adw_id}/reviewer/review_img/export_button.png"
    }
  ]
}
```

**Used by**: `adw_review_iso.py` (review phase)

## Documentation Commands

### `/document` — Generate Feature Documentation
**File**: `document.md`

Creates user-facing feature documentation.

**Arguments**:
- `adw_id` (required)
- `spec_path` (optional): Original spec file
- `documentation_screenshots_dir` (optional): Screenshots to include

**Returns**: JSON with path to created docs

**Model**: Sonnet (base) or Opus (heavy)

**Flow**:
1. Analyzes `git diff origin/main`
2. Reads the spec file
3. Copies screenshots to `app_docs/assets/`
4. Generates `app_docs/feature-{adw_id}-{name}.md` with:
   - Feature overview
   - User guide
   - Screenshots with captions
   - API documentation (if applicable)
5. Updates `conditional_docs.md` with when to read this doc

**Output**: `app_docs/feature-cc73faf1-upload-button-text.md`

**Used by**: `adw_document_iso.py` (documentation phase)

### `/track_agentic_kpis` — Update Performance Metrics
**File**: `track_agentic_kpis.md`

Maintains performance tracking in `app_docs/agentic_kpis.md`.

**Arguments**:
- `state_json` (required): Current ADWState as JSON

**Returns**: Updated KPI file content

**Model**: Sonnet (base and heavy)

**Metrics tracked**:
- **Current Streak**: How many consecutive successful runs
- **Longest Streak**: Historical best streak
- **Total Plan Size**: Sum of all spec file line counts
- **Diff Statistics**: Total added/removed/files modified
- **Average Presence**: How many attempts per issue (1.0 = first try)

**Updates**: `app_docs/agentic_kpis.md` with two tables:
1. Summary Agentic KPIs (streaks, totals, averages)
2. Per-run detail table (one row per ADW ID)

**Used by**: `adw_document_iso.py` (after documentation phase)

### `/conditional_docs` — Documentation Routing Guide
**File**: `conditional_docs.md`

Not a slash command, but a guidance document read by planners.

**Purpose**: Tells agents which feature docs to read based on what they're working on

**Format**:
```markdown
## app/server/core/sql_security.py
When working on SQL injection prevention, read:
- `app_docs/feature-abc123-sql-injection-fixes.md`
- `app_docs/feature-def456-query-validation.md`

## app/client/src/components/ExportButton.tsx
When working on export functionality, read:
- `app_docs/feature-490eb6b5-one-click-table-exports.md`
- `app_docs/feature-cc73faf1-upload-button-text.md`
```

**Used by**: All planning commands (feature, bug, chore) as context

## Git & VCS Commands

### `/commit` — Generate Semantic Commit Message
**File**: `commit.md`

Creates a meaningful commit message from agent + issue context.

**Arguments**:
- `agent_name` (required): Which agent is committing
- `issue_class` (required): "chore" | "bug" | "feature"
- `issue` (required): GitHub issue JSON

**Returns**: Plain-text commit message

**Model**: Haiku (all sets)

**Format**: `<agent_name>: <issue_class>: <present-tense verb> <description>`

**Example**: `sdlc_implementor: feature: add CSV export functionality`

**Actions**:
1. Generates the message
2. Runs `git add -A` in current directory
3. Runs `git commit -m "<message>"`
4. Returns the message string

**Used by**: All phase scripts (after implementing code)

### `/pull_request` — Create GitHub PR
**File**: `pull_request.md`

Creates a GitHub PR linking to the original issue.

**Arguments**:
- `branch_name` (required): Git branch name
- `issue` (required): GitHub issue JSON
- `plan_file` (required): Path to the spec file
- `adw_id` (required): ADW workflow ID

**Returns**: Plain-text PR URL

**Model**: Haiku (all sets)

**PR format**:
- **Title**: `<type>: #<issue_number> - <issue_title>`
  - Example: `feature: #47 - Improve upload button styling`
- **Body**:
  - Linked to original issue
  - References the spec file
  - Includes ADW tracking ID
  - Checklist of validation steps

**Actions**:
1. Generates title and body
2. Runs `gh pr create --title <title> --body <body>`
3. Returns PR URL

**Used by**: `adw_plan_iso.py` (after creating plan) and `adw_build_iso.py` (to update PR)

### `/generate_branch_name` — Create Branch Name
**File**: `generate_branch_name.md`

Generates a semantic git branch name.

**Arguments**:
- `issue_class` (required): "chore" | "bug" | "feature"
- `adw_id` (required): ADW workflow ID
- `issue` (required): GitHub issue JSON

**Returns**: Plain-text branch name

**Model**: Haiku (all sets)

**Format**: `<class>-issue-<number>-adw-<id>-<3-6-word-slug>`

**Examples**:
- `feat-issue-47-adw-cc73faf1-improve-upload-button`
- `fix-issue-48-adw-490eb6b5-handle-csv-export-errors`
- `chore-issue-49-adw-4c768184-refactor-query-parser`

**Used by**: `adw_plan_iso.py` (before creating worktree)

## Classification Commands

### `/classify_issue` — Issue Type Classification
**File**: `classify_issue.md`

Classifies a GitHub issue into type.

**Arguments**:
- `$ARGUMENTS`: GitHub issue JSON (required)

**Returns**: JSON with single `command` field

**Model**: Haiku (all sets)

**Output** (one of):
```json
{"command": "/feature"}
{"command": "/bug"}
{"command": "/chore"}
{"command": "/patch"}
{"command": "0"}  # Don't process
```

**Used by**: `adw_plan_iso.py` (to choose planning template)

### `/classify_adw` — Workflow Command Extraction
**File**: `classify_adw.md`

Extracts embedded ADW workflow commands from free text.

**Arguments**:
- `$ARGUMENTS`: Text from GitHub issue body/comment (required)

**Returns**: JSON with extracted workflow, adw_id, model_set

**Model**: Sonnet (all sets)

**Output**:
```json
{
  "adw_workflow": "adw_sdlc_iso",
  "adw_id": "a1b2c3d4",
  "model_set": "heavy"
}
```

**ZTE Safety Rule**: `/adw_sdlc_zte_iso` is ONLY recognized if `ZTE` is explicitly uppercased in the issue body. Lowercase `zte` is ignored.

**Used by**: `trigger_webhook.py` and `trigger_cron.py` (workflow selection)

## Setup & Infrastructure Commands

### `/install` — Full Project Setup
**File**: `install.md`

One-time setup to initialize the entire ADW system.

**Arguments**: None

**Returns**: Setup complete message

**Model**: Sonnet (all sets)

**Actions**:
1. Reads `.env.sample`, creates `.env` template
2. Runs `prime` to understand the codebase
3. Re-initializes git (removes/re-adds origin)
4. Installs backend deps (`uv sync`)
5. Installs frontend deps (`bun install`)
6. Runs `copy_dot_env.sh` to set up env files
7. Runs `reset_db.sh` to initialize database
8. Starts the server in background

**Used by**: Initial setup only

### `/install_worktree` — Worktree Bootstrap
**File**: `install_worktree.md`

Initializes a new worktree with dependencies.

**Arguments**:
- `worktree_path` (required): Path to the worktree directory
- `backend_port` (required): Allocated backend port
- `frontend_port` (required): Allocated frontend port

**Returns**: Success message

**Model**: Sonnet (all sets)

**Actions**:
1. Creates `.ports.env` with port configuration
2. Copies `.env` files from parent repo
3. Updates `.mcp.json` with absolute paths (critical!)
4. Updates `playwright-mcp-config.json` with absolute paths
5. Installs backend deps in worktree (`uv sync`)
6. Installs frontend deps in worktree (`bun install`)
7. Resets database in worktree

**Used by**: `adw_plan_iso.py` (before running planner)

### `/cleanup_worktrees` — Worktree Management
**File**: `cleanup_worktrees.md`

Lists or removes worktrees.

**Arguments**:
- `action` (required): "list" | "specific" | "all"
- `adw_id` (conditional): Required if action="specific"

**Returns**: List of removed worktrees or message

**Model**: Sonnet (all sets)

**Actions**:
- `list`: `git worktree list`
- `specific adw_id`: `git worktree remove --force trees/{adw_id}`
- `all`: Remove all worktrees under `trees/`

**Used by**: Manual cleanup, or `scripts/purge_tree.sh`

### `/prepare_app` — Pre-Test Application Setup
**File**: `prepare_app.md`

Ensures app is running before review/E2E tests.

**Arguments**: None

**Returns**: App URL (http://localhost:PORT)

**Model**: Sonnet (all sets)

**Actions**:
1. Resets database (`scripts/reset_db.sh`)
2. Reads `.ports.env` to find port (or defaults to 5173)
3. Starts app in background: `nohup sh ./scripts/start.sh`
4. Waits for app to be ready (polls health endpoint)
5. Returns app URL

**Used by**: `/review` and `/test_e2e` commands

### `/start` — Start the Application
**File**: `start.md`

Simple app start command.

**Arguments**: None

**Returns**: App running message + browser URL

**Model**: Sonnet (all sets)

**Actions**:
1. Checks if app is already running
2. Starts if not: `nohup sh ./scripts/start.sh`
3. Opens browser to the app

**Used by**: Manual app startup, or `/in_loop_review`

### `/prime` — Codebase Orientation
**File**: `prime.md`

Quick codebase context for agents.

**Arguments**: None

**Returns**: Context summary

**Model**: Sonnet (all sets)

**Actions**:
1. Lists all project files: `git ls-files`
2. Reads `README.md` (project overview)
3. Reads `adws/README.md` (ADW overview)
4. Reads `conditional_docs.md` (documentation routing)

**Used by**: Start of all planning commands

### `/health_check` — System Health Check
**File**: `health_check.md`

Validates all ADW prerequisites.

**Arguments**: None

**Returns**: Health status JSON

**Model**: Haiku (all sets)

**Checks**:
- ✓ `ANTHROPIC_API_KEY` is set
- ✓ `CLAUDE_CODE_PATH` is set
- ✓ Claude Code CLI is installed
- ✓ `gh` CLI is installed and authenticated
- ✓ `uv` is installed
- ✓ Python environment is working
- ✓ SQLite database exists
- ✓ MCP servers are configured

**Used by**: `01-getting-started.md` (verification step)

### `/tools` — List Built-in Tools
**File**: `tools.md`

Lists all available tools (Read, Write, Bash, etc.).

**Arguments**: None

**Returns**: TypeScript function signatures

**Model**: Haiku (all sets)

**Used by**: Agents needing to understand what tools are available

## Human Review Commands

### `/in_loop_review` — Iterative Review
**File**: `in_loop_review.md`

Opens a branch for human engineer review.

**Arguments**:
- `branch_name` (required): Git branch to review

**Returns**: Browser window to the app

**Model**: Sonnet (all sets)

**Flow**:
1. `git fetch`
2. `git checkout <branch_name>`
3. Runs `/prepare_app` to start the app
4. Opens browser so engineer can manually inspect
5. Engineer can request changes (captured in issue comments)

**Used by**: Manual review workflow (optional in SDLC)

## E2E Test Scenarios

Located in `.claude/commands/e2e/`:

### `test_basic_query.md`
Basic SQL query execution test.

### `test_complex_query.md`
Complex queries with filtering and joins.

### `test_disable_input_debounce.md`
Input debouncing behavior.

### `test_export_functionality.md`
CSV/PDF export features.

### `test_random_query_generator.md`
Random query generation and testing.

### `test_sql_injection.md`
SQL injection prevention validation.

Each file defines:
- User Story (what we're testing)
- Test Steps (numbered Playwright actions)
- Success Criteria (what passes)
- Screenshots to capture

**Used by**: `/test_e2e` command

## Command Invocation Examples

### From Claude Code Session (Interactive)

```
/feature 123 a1b2c3d4 '{"title":"Add export","body":"..."}'
/implement specs/issue-123-...md
/review a1b2c3d4 specs/issue-123-...md reviewer
```

### From ADW Script

```python
from adw_modules.agent import execute_template
from adw_modules.data_types import AgentTemplateRequest

response = execute_template(
    request=AgentTemplateRequest(
        slash_command="/feature",
        arguments=issue_json_string,
        working_dir="trees/a1b2c3d4"
    )
)
```

### From GitHub Comment

```
/adw_plan_build_iso
/patch issue_comment a1b2c3d4 adw_plan_iso
```

## Next Steps

- **Workflow Scripts**: Read `05-workflow-scripts.md` to see how commands are orchestrated
- **Triggering**: Read `06-triggering.md` to understand workflow entry points
- **Operations**: Read `07-operations.md` to monitor and debug
