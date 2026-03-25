# ADW Agentic Layer — Extending the System

This document explains how to add custom functionality to ADW: new commands, phases, pipelines, and hooks.

## Adding a New Slash Command

Slash commands are markdown prompt files in `.claude/commands/`. They define reusable Claude prompts invoked by ADW scripts.

### Step 1: Create Command File

Create `.claude/commands/my_command.md`:

```markdown
# My Custom Command

This command does something specific.

## What It Does

Describe the command's purpose and behavior.

## Arguments

- `$1` or `$ARGUMENTS`: Description of input

## Output

Describe what the command returns (should be JSON or plain text).

## Implementation

The actual prompt to Claude. Tell Claude what to do step-by-step.
```

**Example: `/validate_spec` — Validate a spec file**

```markdown
# Validate Spec File

Checks that a spec file follows ADW format.

## Arguments

- `$ARGUMENTS`: Path to spec file (required)

## Output

Returns JSON: {"valid": true|false, "errors": []}

## Implementation

Read the spec file at the provided path.

Check these required sections:
1. Feature/Bug/Chore description
2. Relevant Files
3. Step-by-Step Tasks
4. Validation Commands

If any section is missing, add it to errors array.

Return JSON with validation result.
```

### Step 2: Register in `SLASH_COMMAND_MODEL_MAP`

Edit `adws/adw_modules/agent.py`:

```python
SLASH_COMMAND_MODEL_MAP = {
    "base": {
        # ... existing commands
        "validate_spec": "sonnet",    # Add your command
    },
    "heavy": {
        # ... existing commands
        "validate_spec": "opus",      # Typically same or upgraded
    }
}
```

**Model selection**:
- `haiku` — fast, deterministic (classify, generate name, commit)
- `sonnet` — standard reasoning (most commands)
- `opus` — advanced reasoning (complex implementations, reviews)

### Step 3: Add to Type Literal

Edit `adws/adw_modules/data_types.py`:

```python
SlashCommand = Literal[
    "/feature",
    "/bug",
    "/chore",
    "/patch",
    "/implement",
    # ... existing
    "/validate_spec",  # Add your command
]
```

### Step 4: Invoke from ADW Script

In your phase script or workflow:

```python
from adw_modules.agent import execute_template
from adw_modules.data_types import AgentTemplateRequest

response = execute_template(
    request=AgentTemplateRequest(
        slash_command="/validate_spec",
        arguments="specs/issue-123-...md",
        working_dir=state.worktree_path,
    )
)

if response.success:
    result = json.loads(response.output)
    if result["valid"]:
        print("Spec is valid!")
    else:
        print(f"Spec errors: {result['errors']}")
```

### Step 5: Test the Command

```bash
# Interactive test
claude -p "/validate_spec specs/issue-123-...md"

# Or run via ADW
uv run adws/adw_build_iso.py 123 a1b2c3d4
```

## Adding a New ADW Phase

Phases are Python scripts that handle one stage of the SDLC.

### Step 1: Create Phase Script

Create `adws/adw_custom_phase_iso.py`:

```python
#!/usr/bin/env -S uv run
"""Custom phase for ADW."""

import sys
import json
from pathlib import Path

from adw_modules.state import ADWState
from adw_modules.agent import execute_template
from adw_modules.data_types import AgentTemplateRequest, ADWExtractionResult
from adw_modules.utils import setup_logger

def main():
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: adw_custom_phase_iso.py <issue_number> [adw_id]")
        sys.exit(1)

    issue_number = int(sys.argv[1])
    adw_id = sys.argv[2] if len(sys.argv) > 2 else None

    # Load state
    try:
        state = ADWState.load(adw_id) if adw_id else ADWState.ensure(issue_number)
    except Exception as e:
        print(f"Error loading state: {e}", file=sys.stderr)
        sys.exit(1)

    # Set up logging
    logger = setup_logger(state.adw_id, "custom_phase")
    logger.info(f"Starting custom phase for issue #{issue_number}")

    # Validate preconditions (e.g., build must be complete)
    if "adw_build_iso" not in state.all_adws:
        logger.error("Build phase must complete before custom phase")
        sys.exit(1)

    # Execute the phase
    try:
        logger.info("Running custom operation...")

        # Call your command
        response = execute_template(
            request=AgentTemplateRequest(
                slash_command="/my_command",
                arguments="some argument",
                working_dir=state.worktree_path,
            )
        )

        if not response.success:
            logger.error(f"Command failed: {response.output}")
            sys.exit(1)

        logger.info(f"Custom phase completed: {response.output}")

        # Update state
        state.all_adws.append("adw_custom_phase_iso")
        state.save("adw_custom_phase_iso")

    except Exception as e:
        logger.error(f"Phase failed: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Custom phase succeeded")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Step 2: Add Phase to Data Types

Edit `adws/adw_modules/data_types.py`:

```python
ADWWorkflow = Literal[
    "adw_plan_iso",
    "adw_build_iso",
    "adw_test_iso",
    "adw_review_iso",
    "adw_document_iso",
    "adw_ship_iso",
    "adw_custom_phase_iso",  # Add your phase
]
```

### Step 3: Make Script Executable

```bash
chmod +x adws/adw_custom_phase_iso.py
```

### Step 4: Test the Phase

```bash
uv run adws/adw_custom_phase_iso.py 123
```

## Adding a New Pipeline

Pipelines chain multiple phases together.

### Step 1: Create Pipeline Script

Create `adws/adw_plan_build_custom_iso.py`:

```python
#!/usr/bin/env -S uv run
"""Pipeline: Plan → Build → Custom Phase"""

import subprocess
import sys
from adw_modules.state import ADWState
from adw_modules.utils import setup_logger

def run_phase(script_name, issue_number, adw_id=None):
    """Run a phase script and return adw_id"""
    cmd = ["uv", "run", f"adws/{script_name}.py", str(issue_number)]
    if adw_id:
        cmd.append(adw_id)

    result = subprocess.run(cmd)
    if result.returncode != 0:
        return None
    return adw_id

def main():
    if len(sys.argv) < 2:
        print("Usage: adw_plan_build_custom_iso.py <issue_number>")
        sys.exit(1)

    issue_number = int(sys.argv[1])

    # Phase 1: Plan
    adw_id = run_phase("adw_plan_iso", issue_number)
    if not adw_id:
        print("Plan phase failed")
        sys.exit(1)

    # Phase 2: Build
    if not run_phase("adw_build_iso", issue_number, adw_id):
        print("Build phase failed")
        sys.exit(1)

    # Phase 3: Custom
    if not run_phase("adw_custom_phase_iso", issue_number, adw_id):
        print("Custom phase failed")
        sys.exit(1)

    print(f"Pipeline completed successfully. ADW ID: {adw_id}")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Step 2: Make Executable

```bash
chmod +x adws/adw_plan_build_custom_iso.py
```

### Step 3: Use the Pipeline

```bash
uv run adws/adw_plan_build_custom_iso.py 123
```

## Adding a New Hook

Hooks are Python scripts that fire on lifecycle events.

### Step 1: Create Hook Script

Create `.claude/hooks/my_hook.py`:

```python
#!/usr/bin/env -S uv run
"""My custom hook."""

import json
import sys
from pathlib import Path
from .utils.constants import ensure_session_log_dir

def main():
    # Read input from Claude Code
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(1)

    session_id = input_data.get("session_id")
    if not session_id:
        sys.exit(1)

    # Get log directory
    log_dir = ensure_session_log_dir(session_id)

    # Do something
    my_data = {
        "timestamp": input_data.get("timestamp"),
        "session_id": session_id,
        "custom_field": "my_value",
    }

    # Write log
    log_file = log_dir / "my_hook.json"
    with open(log_file, "a") as f:
        f.write(json.dumps(my_data) + "\n")

    # Exit 0 to allow, 2 to block
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Step 2: Register in `settings.json`

Edit `.claude/settings.json`:

```json
{
  "hooks": [
    // ... existing hooks
    {
      "name": "MyHook",
      "script": "my_hook.py",
      "matcher": {}
    }
  ]
}
```

**Hook events** (replace with your trigger):
- `PreToolUse` — before every tool call
- `PostToolUse` — after every tool call
- `Notification` — on idle/permission prompts
- `Stop` — when session ends
- `CustomHook` — custom event (if you extend Claude Code)

### Step 3: Test the Hook

```bash
# Hook should fire and create logs/{session_id}/my_hook.json
claude -p "Do something"

# Check logs
cat logs/*/my_hook.json
```

## Modifying Model Assignments

Change which models are used for each command.

### Current Model Map

```python
# In adws/adw_modules/agent.py
SLASH_COMMAND_MODEL_MAP = {
    "base": {
        "/classify_issue": "haiku",
        "/feature": "sonnet",
        "/implement": "sonnet",
        "/review": "sonnet",
        # ...
    },
    "heavy": {
        "/classify_issue": "haiku",
        "/feature": "opus",
        "/implement": "opus",
        "/review": "sonnet",
        # ...
    }
}
```

### Change a Model Assignment

```python
# Upgrade /review to opus in heavy mode
SLASH_COMMAND_MODEL_MAP["heavy"]["/review"] = "opus"

# Or make haiku use sonnet
SLASH_COMMAND_MODEL_MAP["base"]["/classify_issue"] = "sonnet"
```

**When to upgrade**:
- Command is producing low-quality output
- Too many retries needed
- Task is complex and needs better reasoning

**When to downgrade**:
- Cost is too high
- Command is deterministic (doesn't need advanced reasoning)

### Test Model Change

```bash
# Build will use the new model
uv run adws/adw_build_iso.py 123 a1b2c3d4
```

## Adding a New E2E Test Scenario

E2E tests use Playwright for browser automation.

### Step 1: Create Test File

Create `.claude/commands/e2e/test_my_feature.md`:

```markdown
# E2E Test: My Feature

## User Story

As a user, I can do something specific and get the expected result.

## Test Steps

1. Navigate to http://localhost:FRONTEND_PORT
2. Find element with ID "my-button"
3. Click the button
4. Wait for page to load (max 5 seconds)
5. Verify alert message appears
6. Screenshot: my_feature_success.png

## Success Criteria

- Page loads without errors
- Alert message is visible
- Alert contains text "Success!"
- Response time < 3 seconds
```

### Step 2: Use in Plan

When creating feature plan, `/feature` command checks for UI changes and creates appropriate E2E test file.

### Step 3: Run the Test

```bash
# Via /test_e2e command
/test_e2e a1b2c3d4 sdlc_reviewer .claude/commands/e2e/test_my_feature.md

# Or in an E2E phase
uv run adws/adw_test_iso.py 123 a1b2c3d4  # Includes all E2E tests
```

## Adding Custom Environment Variables

ADW respects environment variables for configuration.

### Add to `.env`

```bash
# In .env (gitignored)
MY_CUSTOM_VAR=my_value
MY_API_KEY=...
```

### Use in Hook or Script

```python
import os

my_var = os.getenv("MY_CUSTOM_VAR")
if my_var:
    print(f"Custom var: {my_var}")
```

### Pass to Claude Code Safely

Use `get_safe_subprocess_env()`:

```python
from adw_modules.utils import get_safe_subprocess_env

env = get_safe_subprocess_env()
env["MY_CUSTOM_VAR"] = os.getenv("MY_CUSTOM_VAR")

subprocess.run(["uv", "run", "..."], env=env)
```

This filters the environment to only pass safe variables (prevents secrets leakage).

## Adding Custom Logging

ADW uses Python's `logging` module.

### In a Hook

```python
import logging
from .utils.constants import ensure_session_log_dir

log_dir = ensure_session_log_dir(session_id)
log_file = log_dir / "my_custom.log"

logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("my_hook")
logger.info("Something happened")
```

### In a Phase Script

```python
from adw_modules.utils import setup_logger

logger = setup_logger(adw_id, "my_phase")
logger.info("Phase started")
logger.debug("Debug info")
logger.warning("Warning message")
logger.error("Error occurred")
```

Logs go to both console (INFO+) and `agents/{adw_id}/my_phase/execution.log` (DEBUG+).

## Creating a Trigger

Custom triggers can invoke ADW workflows based on external events.

### Template: Event-Based Trigger

```python
#!/usr/bin/env -S uv run
"""Trigger ADW from external source"""

import subprocess
from adw_modules.github import fetch_open_issues
from adw_modules.utils import setup_logger

def main():
    logger = setup_logger("custom_trigger", "trigger")

    # Poll external source or listen for events
    while True:
        # Example: fetch GitHub issues with label "ready-for-adw"
        issues = fetch_open_issues()
        for issue in issues:
            if "ready-for-adw" in [label.name for label in issue.labels]:
                logger.info(f"Starting ADW for issue #{issue.number}")

                # Trigger workflow
                subprocess.run([
                    "uv", "run", "adws/adw_plan_build_iso.py",
                    str(issue.number)
                ])

        # Sleep before polling again
        time.sleep(60)

if __name__ == "__main__":
    main()
```

## Best Practices

### When Adding Commands

- **Keep commands focused**: Each command should do one thing well
- **Return structured output**: Use JSON for complex results
- **Document arguments**: Be explicit about what each arg does
- **Handle errors gracefully**: Return error JSON, don't crash
- **Test independently**: `/feature 123 a1b2c3d4 '...'` should work standalone

### When Adding Phases

- **Validate preconditions**: Check that previous phases completed
- **Update state after success**: Append to `all_adws` list
- **Log extensively**: Debug logs help with troubleshooting
- **Don't modify main branch**: Work in worktree only
- **Return non-zero exit code on failure**: For pipeline detection

### When Adding Pipelines

- **Chain via subprocess**: Don't import/call directly (isolation)
- **Pass adw_id between phases**: Maintain state continuity
- **Stop on fatal error**: Return non-zero immediately
- **Allow non-fatal failures**: Log but continue (optional)
- **Document the flow**: Explain phase order and dependencies

### When Adding Hooks

- **Keep hooks fast**: Don't do heavy processing
- **Log to structured JSON**: Append-only (don't truncate)
- **Exit 0 to allow**: Exit 2 to block execution
- **Don't modify files unnecessarily**: Logs only
- **Handle missing context**: Gracefully if fields missing

## Testing Extensions

### Unit Test Your Command

```bash
# Direct invocation
claude -p "/my_command arg1 arg2"

# Check output
# Should be properly formatted (JSON or plain text)
```

### Integration Test with ADW

```bash
# Create a test issue
gh issue create --title "Test" --body "test_adw_custom"

# Run workflow
uv run adws/adw_plan_iso.py 123

# Check state
cat agents/{adw_id}/adw_state.json

# Check logs
tail -50 agents/{adw_id}/*/execution.log
```

### End-to-End Test

```bash
# Full pipeline with your custom phase
uv run adws/adw_plan_build_custom_iso.py 123

# Verify in GitHub
gh issue view 123 --web
```

## Documentation

When adding features, document them:

1. **Command**: Add to `04-slash-commands.md` with args/return/use cases
2. **Phase**: Add to `05-workflow-scripts.md` with flow diagram
3. **Trigger**: Add to `06-triggering.md` with setup steps
4. **Operations**: Add to `07-operations.md` if operationally significant

Example update to `04-slash-commands.md`:

```markdown
### `/my_command` — My Command
**File**: `my_command.md`

Does something specific.

**Arguments**:
- `$ARGUMENTS`: My input (required)

**Returns**: Plain-text result or JSON

**Model**: Sonnet (all sets)

**Used by**: My custom phase
```

## Next Steps

- Review existing commands in `.claude/commands/`
- Review existing phases in `adws/adw_*_iso.py`
- Study `adw_modules/` to understand the architecture
- Test your extension thoroughly
- Document it for the team
