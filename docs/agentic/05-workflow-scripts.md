# ADW Agentic Layer — Workflow Scripts

This document explains all ADW Python scripts: phase scripts, pipelines, and core modules.

## Phase Scripts

Each phase script handles one stage of the SDLC. They follow a consistent pattern:
1. Parse arguments (issue number, optional ADW ID)
2. Load/create state
3. Validate preconditions
4. Execute the phase
5. Save state
6. Return status

### `adw_plan_iso.py` — Planning Phase

**Entry point**: The first phase. Creates the worktree.

**Arguments**:
```bash
uv run adws/adw_plan_iso.py <issue_number> [adw_id]
```

**Flow**:
1. `ensure_adw_id()` — creates 8-char ID, initializes state
2. `fetch_issue()` — gets issue JSON from GitHub
3. Post to GitHub: "Starting isolated planning phase"
4. `classify_issue()` — calls `/classify_issue` → `/feature`, `/bug`, `/chore`
5. `generate_branch_name()` — calls `/generate_branch_name`
6. `create_worktree()` — `git worktree add -b {branch} trees/{adw_id} origin/main`
7. `setup_worktree_environment()` — creates `.ports.env`, allocates ports
8. Call `/install_worktree` — sets up worktree (deps, MCP config)
9. `build_plan()` — calls `/feature`, `/bug`, or `/chore` → creates spec file
10. Validate spec file exists
11. `create_commit()` — commits the spec
12. `finalize_git_operations()` — pushes, creates PR, posts progress
13. Save full state

**State fields populated**:
- ✓ `adw_id`
- ✓ `issue_number`
- ✓ `branch_name`
- ✓ `plan_file`
- ✓ `issue_class`
- ✓ `worktree_path`
- ✓ `backend_port`
- ✓ `frontend_port`
- ✓ `model_set`
- ✓ `all_adws` = ["adw_plan_iso"]

**Output**: Logs to `agents/{adw_id}/sdlc_planner/raw_output.jsonl` and console

**Failure modes**:
- Issue not found → exit with error
- Worktree creation fails → exit with error
- Planner times out → retry up to 3 times
- Spec file not created → exit with error

### `adw_build_iso.py` — Implementation Phase

**Arguments**:
```bash
uv run adws/adw_build_iso.py <issue_number> [adw_id]
```

**Preconditions**: `adw_plan_iso.py` must have completed (state file exists with plan_file set)

**Flow**:
1. Load state from `agents/{adw_id}/adw_state.json`
2. Validate worktree exists (`git worktree list` includes path)
3. Validate plan file exists (`git status` in spec/`)
4. `implement_plan()` — calls `/implement {plan_file}` in worktree
5. Wait for implementation to complete
6. `create_commit()` — commits the code changes
7. `finalize_git_operations()` — pushes, updates PR
8. Save state with `all_adws.append("adw_build_iso")`

**State fields after**:
- All fields from plan_iso remain
- ✓ `all_adws` = ["adw_plan_iso", "adw_build_iso"]

**Output**: Logs to `agents/{adw_id}/sdlc_implementor/raw_output.jsonl`

**Failure modes**:
- State not found → exit with error
- Worktree missing → exit with error
- Implementation fails → retry up to 3 times
- Commit fails → exit with error

### `adw_test_iso.py` — Testing Phase

**Arguments**:
```bash
uv run adws/adw_test_iso.py <issue_number> [adw_id] [--skip-e2e]
```

**Preconditions**: Build phase must be complete

**Flow**:
1. Load state
2. Validate worktree
3. Call `/test` in worktree → runs pytest, tsc, build
4. On failure:
   - Call `/resolve_failed_test` with the failure JSON
   - Retry the specific test
   - If still fails, either continue or abort (configurable)
5. If `--skip-e2e` not set:
   - For each E2E test file:
     - Call `/test_e2e {test_file}` in worktree
     - On failure: call `/resolve_failed_e2e_test`
6. Commit any test fixes
7. Push
8. Save state

**State fields after**:
- ✓ `all_adws` = [..., "adw_test_iso"]

**Configuration**:
- `--skip-e2e`: Don't run browser tests (used by `adw_sdlc_iso`)
- `--skip-resolution`: Don't auto-fix failures (used for analysis)

**Failure modes**:
- Test fails, cannot be fixed → log failure, continue or abort (depends on pipeline)

### `adw_review_iso.py` — Review Phase

**Arguments**:
```bash
uv run adws/adw_review_iso.py <issue_number> [adw_id]
```

**Preconditions**: Build phase complete (tests pass optional)

**Flow**:
1. Load state
2. Validate worktree
3. Find spec file from state or git diff
4. Loop up to 3 times (patch retry loop):
   a. Call `/review {spec_file}` in worktree
   b. Parse ReviewResult JSON
   c. If `success: true`, break loop
   d. If blockers found:
      - Call `/patch` to create patch plan
      - Call `/implement` to implement patch
      - Commit patch changes
      - Loop back for re-review
   e. If blockers still exist after 3 attempts, fail
5. On final success:
   - Collect all screenshots
   - Upload to R2 (if creds set) or use local paths
   - Format review summary with inline images
   - Post comprehensive review comment to GitHub
6. Commit and push
7. Save state

**State fields after**:
- ✓ `all_adws` = [..., "adw_review_iso"]

**Screenshot handling**:
- Local: `agents/{adw_id}/reviewer/review_img/`
- Cloud: Upload to `tac-public-imgs.iddagents.com/adw/{adw_id}/`

**Failure modes**:
- Review fails and cannot be auto-patched → pipeline aborts
- R2 upload fails → falls back to local paths
- Screenshot capture fails → log error, continue

### `adw_document_iso.py` — Documentation Phase

**Arguments**:
```bash
uv run adws/adw_document_iso.py <issue_number> [adw_id]
```

**Preconditions**: Review phase complete

**Flow**:
1. Load state
2. Validate worktree
3. Find spec file
4. Call `/document {spec_file}` in worktree
   - Claude analyzes git diff
   - Reads the spec
   - Copies any screenshots
   - Generates `app_docs/feature-{adw_id}-{name}.md`
   - Updates `conditional_docs.md`
5. Call `/track_agentic_kpis` with state JSON
   - Updates `app_docs/agentic_kpis.md` with KPI tables
6. Commit doc changes
7. Push
8. Save state

**State fields after**:
- ✓ `all_adws` = [..., "adw_document_iso"]

**Generated files**:
- `app_docs/feature-{adw_id}-*.md` — user-facing feature docs
- `app_docs/agentic_kpis.md` — performance metrics table

**Failure modes**:
- Documentation generation fails → log error, continue (non-fatal)

### `adw_ship_iso.py` — Shipping Phase (ZTE Only)

**Arguments**:
```bash
uv run adws/adw_ship_iso.py <issue_number> [adw_id]
```

**Preconditions**: All phases complete (full SDLC state)

**Important**: This is the only phase that modifies the **main branch**. All previous phases work in the worktree.

**Validation**:
```python
# All 8 state fields must be non-null
required_fields = [
    adw_id, issue_number, branch_name, plan_file, issue_class,
    worktree_path, backend_port, frontend_port, model_set
]
if any(field is None for field in required_fields):
    raise ValidationError("Incomplete state: cannot ship")
```

**Flow**:
1. Load state
2. Validate all state fields are populated
3. Validate worktree still exists
4. Find PR for the branch
5. Approve PR: `gh pr review --approve`
6. Merge PR: `gh pr merge --squash`
7. In **main repo root** (not worktree):
   - `git fetch`
   - `git checkout main`
   - `git pull origin main` (gets the merged commit)
8. Post "🎉 Merged!" comment to GitHub
9. Clean up worktree: `git worktree remove --force`
10. Cleanup database/temporary state

**State fields after**:
- ✓ `all_adws` = [..., "adw_ship_iso"] (complete pipeline)

**Failure modes**:
- PR already merged → check and proceed
- Merge conflicts → cannot auto-resolve, abort
- Branch protection rules → cannot merge, abort
- Worktree missing → cleanup what exists

### `adw_patch_iso.py` — Standalone Patch Workflow

**Arguments**:
```bash
uv run adws/adw_patch_iso.py <issue_number> [adw_id]
```

**Special purpose**: Create and implement a quick patch without full SDLC.

**Use case**: Issue comment says "The font size is wrong", need quick fix without going through plan/test/review.

**Flow**:
1. Load state (if adw_id provided) or create new
2. Fetch issue
3. Call `/patch` with review_change_request
4. Call `/implement` on the patch plan
5. Commit and push
6. Return patch summary

**Simpler than full SDLC**: No testing, no review loop, no documentation.

## Pipeline Orchestrators

Pipeline orchestrators chain individual phase scripts together via `subprocess.run()`. They:
1. Run phase 1
2. Check exit code
3. If success, run phase 2 (passing adw_id)
4. Continue until all phases complete or one fails

### `adw_plan_build_iso.py`
```
Plan → Build
```
Two-phase workflow for straightforward changes.

### `adw_plan_build_test_iso.py`
```
Plan → Build → Test
```
Three-phase workflow with test validation.

### `adw_plan_build_review_iso.py`
```
Plan → Build → Review
```
Review without testing.

### `adw_plan_build_test_review_iso.py`
```
Plan → Build → Test → Review
```
Full development workflow with tests and review.

### `adw_plan_build_document_iso.py`
```
Plan → Build → Document
```
No tests, straight to documentation.

## SDLC Orchestrators

### `adw_sdlc_iso.py` — Standard SDLC

```
Plan → Build → Test → Review → Document
```

**Behavior**:
- Test failures are logged but **don't stop** the pipeline
- Review blockers **do stop** the pipeline
- Documentation failures are logged but **don't stop**

**Arguments**:
```bash
uv run adws/adw_sdlc_iso.py <issue_number> [adw_id] [--skip-e2e] [--skip-resolution]
```

**Return**: ADW state with all phases completed

### `adw_sdlc_zte_iso.py` — Zero Touch Execution (Auto-Merge)

```
Plan → Build → Test → Review → Document → Ship
```

**Behavior**:
- Test failures **stop** the pipeline
- Review failures **stop** the pipeline
- Documentation failures are logged but **don't stop** (continue to ship)

**Arguments**:
```bash
uv run adws/adw_sdlc_zte_iso.py <issue_number> [adw_id]
```

**Critical Safety Features**:
1. **Requires explicit uppercase `ZTE`** in GitHub issue body
   - `adw_sdlc_ZTE_iso` ✓ triggers
   - `adw_sdlc_zte_iso` ✗ does NOT trigger
2. **Posts warning comment** when started
3. **Aborts immediately** on any blocker
4. **Posts abort reason** if stopped

**Flow**:
```python
try:
    adw_plan_iso(issue_number)
    adw_build_iso(issue_number, adw_id)
    adw_test_iso(issue_number, adw_id)  # Fails on test error
    adw_review_iso(issue_number, adw_id) # Fails on blocker
    adw_document_iso(issue_number, adw_id) # Doesn't fail
    adw_ship_iso(issue_number, adw_id)  # Merges to main!
except Exception as e:
    post_comment(issue, f"Workflow aborted: {e}")
    raise
```

## Core Modules

### `adw_modules/agent.py`

**Responsibility**: Bridge between ADW and Claude Code CLI.

**Key exports**:

**`SLASH_COMMAND_MODEL_MAP`** — Model assignments:
```python
SLASH_COMMAND_MODEL_MAP = {
    "base": {
        "/classify_issue": "haiku",
        "/feature": "sonnet",
        "/implement": "sonnet",
        "/test": "sonnet",
        "/review": "sonnet",
        "/document": "sonnet",
        # ... etc
    },
    "heavy": {
        "/classify_issue": "haiku",
        "/feature": "opus",     # Upgraded
        "/implement": "opus",   # Upgraded
        # ... rest upgraded where applicable
    }
}
```

**`execute_template(request: AgentTemplateRequest) → AgentPromptResponse`**

Main function. Invokes Claude Code with a slash command.

```python
response = execute_template(
    request=AgentTemplateRequest(
        slash_command="/feature",
        arguments='{"title":"..."}',
        working_dir="trees/a1b2c3d4",
        model_set="base",
    )
)

# Returns:
AgentPromptResponse(
    output="specs/issue-123-...-feature.md",
    success=True,
    session_id="...",
    retry_code=None
)
```

**`prompt_claude_code(request) → str`**

Low-level invocation. Builds `claude -p <prompt> --model <model>` command, streams output to JSONL, parses result.

**`prompt_claude_code_with_retry(request, max_retries=3) → str`**

Wraps `prompt_claude_code` with exponential backoff (1s, 3s, 5s).

Retries on: `CLAUDE_CODE_ERROR`, `TIMEOUT_ERROR`, `EXECUTION_ERROR`, `ERROR_DURING_EXECUTION`

### `adw_modules/state.py`

**Responsibility**: Persistent state management.

**Key class**:

**`ADWState`**:
```python
@dataclass
class ADWState:
    adw_id: str
    issue_number: int
    branch_name: str
    plan_file: str
    issue_class: str  # "chore" | "bug" | "feature"
    worktree_path: str
    backend_port: int
    frontend_port: int
    model_set: str    # "base" | "heavy"
    all_adws: List[str]  # Phases that ran

    @classmethod
    def load(cls, adw_id: str) -> "ADWState":
        """Load from agents/{adw_id}/adw_state.json"""

    def save(self, workflow_step: str = None):
        """Save to agents/{adw_id}/adw_state.json"""

    def update(**kwargs):
        """Update specific fields"""

    def get_working_directory() -> Path:
        """Return worktree_path or project root"""

    def append_adw_id(adw_id: str):
        """Track which workflows ran"""
```

### `adw_modules/workflow_ops.py`

**Responsibility**: Orchestration logic combining all modules.

**Key functions**:

**`classify_issue(issue, adw_id) → str`**
Calls `/classify_issue` command, returns `/chore` or `/bug` or `/feature`

**`build_plan(issue, command, adw_id) → str`**
Calls `/feature` `/bug` `/chore`, returns spec file path

**`implement_plan(plan_file, adw_id) → str`**
Calls `/implement {plan_file}`, returns diff summary

**`generate_branch_name(issue, issue_class, adw_id) → str`**
Calls `/generate_branch_name`, returns branch name

**`create_commit(agent_name, issue, issue_class, adw_id) → str`**
Calls `/commit`, stages and commits changes

**`create_pull_request(branch_name, issue, state) → str`**
Calls `/pull_request`, returns PR URL

**`ensure_adw_id(issue_number, existing_id=None) → str`**
Generates or loads ADW ID, initializes state

**`extract_adw_info(text) → ADWExtractionResult`**
Uses `/classify_adw` to extract workflow + model_set from issue body

### `adw_modules/worktree_ops.py`

**Responsibility**: Git worktree and port management.

**Key functions**:

**`create_worktree(adw_id, branch_name) → Path`**
Runs `git worktree add`, returns path

**`validate_worktree(adw_id, state) → bool`**
Checks: directory exists, git knows about it

**`setup_worktree_environment(worktree_path, backend_port, frontend_port)`**
Creates `.ports.env` with port assignments

**`get_ports_for_adw(adw_id) → (int, int)`**
Deterministic port assignment: `int(adw_id[:8], 36) % 15 + base`

**`find_next_available_ports(adw_id) → (int, int)`**
Fallback if deterministic port is in use

### `adw_modules/data_types.py`

**Responsibility**: Pydantic models for type safety.

**Key types**:
- `ADWStateData` — State schema
- `GitHubIssue`, `GitHubComment`, `GitHubUser` — GitHub API types
- `ReviewResult`, `ReviewIssue` — Review output
- `TestResult`, `E2ETestResult` — Test results
- `AgentPromptRequest`, `AgentPromptResponse` — Claude Code I/O
- `SlashCommand` — Literal type of all command names
- `ModelSet` — `"base"` | `"heavy"`
- `ADWWorkflow` — All pipeline names

### `adw_modules/github.py`

**Responsibility**: GitHub CLI operations.

**Key functions**:
- `fetch_issue(issue_number)` → `GitHubIssue`
- `fetch_issue_comments(issue_number)` → `List[GitHubComment]`
- `make_issue_comment(issue_id, comment)` → `str` (comment ID)
- `mark_issue_in_progress(issue_id)` → adds label + assigns
- `find_keyword_from_comment(keyword, issue)` → latest matching comment

**Loop prevention**: All comments prefixed with `[ADW-AGENTS]`

### `adw_modules/git_ops.py`

**Responsibility**: Git operations with `cwd` support (for worktrees).

**Key functions**:
- `get_current_branch(cwd)` → branch name
- `create_branch(branch_name, cwd)` → creates and checks out
- `commit_changes(message, cwd)` → git add + commit
- `push_branch(branch_name, cwd)` → git push
- `check_pr_exists(branch_name)` → `bool`
- `finalize_git_operations(state, cwd)` → push + create PR

**All functions accept `cwd` parameter** for worktree context.

### `adw_modules/utils.py`

**Responsibility**: Shared utilities.

**Key functions**:
- `make_adw_id() → str` — generates 8-char hex ID
- `setup_logger(adw_id) → logging.Logger`
- `parse_json(text, target_type)` — robust JSON parser
- `check_env_vars(logger)` — validates required env vars
- `get_safe_subprocess_env() → dict` — filters env for subprocesses (removes secrets)

### `adw_modules/r2_uploader.py`

**Responsibility**: Cloudflare R2 screenshot uploads.

**Key class**:

**`R2Uploader`**:
```python
class R2Uploader:
    def __init__(self):
        # Self-initializes if creds are set
        self.bucket_name = os.getenv("CLOUDFLARE_R2_BUCKET_NAME")
        self.enabled = all([creds_present])

    def upload(self, file_path: Path, adw_id: str) → str | None:
        """Upload to R2, return public URL or None if disabled"""
```

Uses Cloudflare API to upload review screenshots to public URL (`tac-public-imgs.iddagents.com`).

Gracefully disables if credentials missing (falls back to local paths).

## Script Execution Patterns

### Pattern 1: Direct Phase Script

```bash
uv run adws/adw_plan_iso.py 123
# Creates worktree, runs planner, outputs: adw_id and spec file path
```

### Pattern 2: Pipeline (Subprocess Chaining)

```python
# adw_plan_build_iso.py
if subprocess.run(["uv", "run", "adws/adw_plan_iso.py", "123"]).returncode == 0:
    # Get adw_id from agents directory
    if subprocess.run(["uv", "run", "adws/adw_build_iso.py", "123", adw_id]).returncode == 0:
        print("Success!")
```

### Pattern 3: With Subprocess Isolation

All ADW subprocess calls use `get_safe_subprocess_env()`:

```python
env = get_safe_subprocess_env()
result = subprocess.run(
    ["uv", "run", "adws/adw_build_iso.py", "123", adw_id],
    env=env,  # Only required vars passed
    capture_output=True
)
```

## Error Handling & Retry Logic

### Retryable Errors

`prompt_claude_code_with_retry()` retries on:
- `CLAUDE_CODE_ERROR` — Claude CLI crashed
- `TIMEOUT_ERROR` — Command took too long
- `EXECUTION_ERROR` — Tool execution failed
- `ERROR_DURING_EXECUTION` — Tool raised exception

Retries: 3 times with delays [1s, 3s, 5s]

### Non-Retryable Errors

Exit immediately:
- `VALIDATION_ERROR` — Invalid input
- `PERMISSION_ERROR` — Access denied
- `NOT_FOUND_ERROR` — File/issue not found
- `STATE_ERROR` — State file corrupted

## Next Steps

- **Triggering**: Read `06-triggering.md` to see how workflows are started
- **Operations**: Read `07-operations.md` to monitor and debug
- **Extending**: Read `08-extending.md` to add new phases/pipelines
