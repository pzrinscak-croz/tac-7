# ADW Agentic Layer — Overview

## What Is This System?

The **AI Developer Workflow (ADW)** system is a fully autonomous software development pipeline that processes GitHub issues end-to-end: from issue creation through planning, implementation, testing, review, documentation, and (optionally) auto-merge to production.

It is built on top of **Claude Code** — Anthropic's AI CLI that can invoke tools, run commands, and read/write code. The ADW system acts as an orchestration layer that composes Claude Code into a multi-phase SDLC workflow.

### The Problem It Solves

Manual software development involves repetitive, well-defined phases:
1. **Plan** — understand requirements, design solution, create spec
2. **Build** — implement code changes
3. **Test** — run test suite, fix failures
4. **Review** — verify implementation matches spec, take screenshots, report issues
5. **Document** — write user-facing docs and update KPI tracking
6. **Ship** — merge to production

For simple, well-scoped tasks, each phase is straightforward and could be handled by an AI. ADW automates all of them by orchestrating Claude as specialized agents (planner, implementor, tester, reviewer, documenter).

### Why This Matters

- **Velocity**: Feature cycles go from days to minutes. No waiting for developers.
- **Consistency**: Every workflow runs the same way. Every issue gets full coverage (tests, review, docs).
- **Debuggability**: Complete logs and state snapshots mean any failure can be diagnosed instantly.
- **Scalability**: Up to 15 workflows run in parallel without interference, via git worktrees.

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                      GitHub Issue (Web)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
         ┌──────────▼────────────┐    ┌─▼──────────────────┐
         │  trigger_webhook.py   │    │  trigger_cron.py   │
         │  (Real-time FastAPI)  │    │  (20s Poll)        │
         └──────────┬────────────┘    └─┬──────────────────┘
                    │                   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼──────────────┐
                    │  ADW Entry Point        │
                    │  (adw_sdlc_iso.py)     │
                    └─────────┬──────────────┘
                              │
        ┌─────────┬───────────┼───────────┬─────────┐
        │         │           │           │         │
    ┌───▼──┐ ┌───▼──┐ ┌──────▼──┐ ┌──────▼──┐ ┌──────▼──┐
    │ Plan │ │Build │ │  Test   │ │ Review  │ │Document │
    └───┬──┘ └───┬──┘ └──────┬──┘ └──────┬──┘ └──────┬──┘
        │        │           │           │           │
        └────────┼───────────┼───────────┼───────────┘
                 │
        ┌────────▼──────────┐
        │ Ship (ZTE only)    │
        └────────┬───────────┘
                 │
        ┌────────▼──────────┐
        │  main branch       │
        │  (Merged PR)       │
        └────────────────────┘

Each phase runs in an isolated git worktree:
    trees/<adw_id>/ ← complete repo copy with own ports + branch
```

## Components

### `.claude/` — Claude Code Configuration
- **`settings.json`**: Permissions (allow/deny CLI commands) and lifecycle hook registration
- **`hooks/`**: 7 Python scripts that fire on every Claude Code event (tool use, session end, user message)
- **`commands/`**: 28+ markdown files defining slash commands. Each becomes a Claude prompt.

**Role**: Safety layer + instruction vocabulary. Hooks block dangerous operations; commands provide reusable prompts.

### `adws/` — The ADW System Core
- **`adw_modules/`**: Core library (agent.py, state.py, data_types.py, etc.)
- **`adw_*_iso.py`**: Phase scripts (plan, build, test, review, document, ship)
- **`adw_triggers/`**: Entry points (webhook, cron)

**Role**: Orchestrates Claude Code into a multi-phase pipeline. Manages state, worktrees, ports.

### `specs/` — Implementation Plans
Created by the planner agent. Named `issue-{N}-adw-{id}-sdlc_planner-{name}.md`. Contains:
- Feature/bug/chore description
- Relevant files to modify
- Step-by-step implementation tasks
- Validation commands

**Role**: Spec file is the contract between planner and implementor. Implementor reads it verbatim.

### `agents/` — Runtime State & Logs (Created at startup)
```
agents/
└── {adw_id}/
    ├── adw_state.json           ← Persistent state (plan path, branch, ports, model_set)
    ├── sdlc_planner/
    │   └── raw_output.jsonl     ← Claude Code JSONL session transcript
    ├── sdlc_implementor/
    │   └── raw_output.jsonl
    ├── reviewer/
    │   └── review_img/          ← Screenshots from Playwright
    └── documenter/
        └── raw_output.jsonl
```

**Role**: Per-run state and agent session logs. `adw_state.json` persists between phases via subprocess calls.

### `logs/` — Session Telemetry (Hook Logs)
```
logs/
└── {session_id}/
    ├── user_prompt_submit.json  ← Every user prompt
    ├── pre_tool_use.json        ← Every tool call (before execution)
    ├── post_tool_use.json       ← Every tool result
    ├── chat.json                ← Full session transcript
    ├── stop.json                ← Session end event
    └── notification.json        ← Permission prompts, idle alerts
```

**Role**: Complete audit trail of all Claude Code sessions. Enables debugging and observability.

### `app_docs/` — Generated Documentation
- `agentic_kpis.md`: Performance metrics (plan size, diff size, success streak, attempts)
- `feature-{adw_id}-{name}.md`: User-facing feature docs created by `/document` command
- `assets/`: Screenshots from review phases

**Role**: Self-documentation layer. System tracks its own performance and generates docs automatically.

### `app/` — The Target Application
FastAPI backend + Vite/TypeScript frontend. Converts natural language to SQL queries. ADW automates this application.

## Key Design Principles

### 1. Isolation via Git Worktrees
Each ADW run creates `trees/{adw_id}/` — a completely isolated copy of the repo with:
- Its own git branch
- Its own `.env` files
- Its own ports (backend + frontend, deterministically allocated)
- Its own MCP config (absolute paths for Playwright)

**Why**: 15 ADW workflows can run in parallel without interfering with each other.

### 2. State as the API
All communication between phases happens via `agents/{adw_id}/adw_state.json`:
- Phase 1 (Plan) writes: `plan_file`, `branch_name`, `worktree_path`, `ports`, `issue_class`, `model_set`
- Phase 2 (Build) reads state, implements plan, keeps all fields
- Phase 3 (Test) reads state, runs tests, appends test results

**Why**: Phases are subprocess calls, not direct function calls. State file is the only shared memory.

### 3. Slash Command Vocabulary
Every Claude action maps to a markdown file in `.claude/commands/`. Example:
- `/feature` → `.claude/commands/feature.md` → Claude researches codebase + creates spec
- `/implement` → `.claude/commands/implement.md` → Claude reads spec + implements code
- `/review` → `.claude/commands/review.md` → Claude uses Playwright + compares to spec

**Why**: Decouples prompting logic from orchestration. Prompts are inspectable and independently tunable.

### 4. Model Tiering
Cheap, deterministic tasks use `haiku` (fast, cheap):
- `/classify_issue` (haiku) → returns `/bug` or `/feature`
- `/generate_branch_name` (haiku) → returns `feat-issue-123-...`
- `/commit` (haiku) → generates a semantic commit message

Complex tasks use `sonnet` or `opus` depending on `model_set`:
- `/implement` (sonnet/opus) → transforms code based on spec
- `/review` (sonnet) → compares implementation to spec
- `/feature` or `/bug` (sonnet/opus) → generates comprehensive plan

**Why**: Optimizes cost. Cheap tasks are deterministic and don't need advanced reasoning.

### 5. Loop Prevention via Bot Identifier
Every GitHub comment posted by ADW is prefixed with `[ADW-AGENTS]`. The webhook trigger filters:
- Comments containing `[ADW-AGENTS]` (bot's own messages)
- Comments matching regex `^[a-f0-9]{8}_\w+[_:]` (progress updates)

**Why**: Prevents the system from re-triggering itself on its own messages.

### 6. Security Layer via Hooks
The `pre_tool_use.py` hook fires before every Claude tool call and blocks:
- `.env` file access (prevents credential leakage)
- `rm -rf` commands (prevents accidental repo destruction)

**Why**: Claude cannot bypass these hooks — they run at the OS level before tool execution.

## Complete Workflow Example: Full SDLC

A user opens a GitHub issue:
```
Title: "Improve upload button styling"
Body: "adw_sdlc_ZTE_iso model_set heavy"
```

**Trigger**: GitHub webhook → `trigger_webhook.py` detects `adw_` in body

**Plan Phase** (`adw_plan_iso.py`):
1. Creates `trees/{adw_id}/` (isolated worktree)
2. Allocates backend port 9100 + frontend port 9200
3. Calls `/install_worktree` → installs deps in worktree
4. Calls `/classify_issue` (haiku) → returns `/feature`
5. Calls `/generate_branch_name` (haiku) → returns `feat-issue-47-abc12345-improve-upload-button`
6. Calls `/feature` (opus, because `model_set=heavy`) → creates `specs/issue-47-adw-abc12345-sdlc_planner-improve-upload-button.md`
7. Commits spec in worktree, pushes, creates PR
8. Posts progress comment to GitHub

**Build Phase** (`adw_build_iso.py`):
1. Loads state (now has plan path + branch + worktree)
2. Calls `/implement specs/...md` (opus) → Claude reads spec, modifies CSS + HTML
3. Commits changes, pushes

**Test Phase** (`adw_test_iso.py`):
1. Calls `/test` (sonnet) → runs pytest, tsc, build
2. All pass ✓

**Review Phase** (`adw_review_iso.py`):
1. Calls `prepare_app` (starts app on port 9200)
2. Calls `/review` (sonnet + Playwright) → takes 3 screenshots of the new button, compares to spec
3. All match ✓

**Document Phase** (`adw_document_iso.py`):
1. Calls `/document` (opus) → generates `app_docs/feature-abc12345-improve-upload-button.md`
2. Updates `app_docs/agentic_kpis.md` with metrics

**Ship Phase** (`adw_ship_iso.py`, ZTE only):
1. Validates all state fields are populated
2. Approves PR (in main repo root)
3. Merges to main
4. Posts "🎉 Merged to production!" to GitHub

**Total time**: ~2 minutes. Zero human touches.

## Next Steps

- **Getting Started**: See `01-getting-started.md` to set up and run your first workflow
- **Core Concepts**: See `02-core-concepts.md` to understand ADW ID, state, worktrees, model sets
- **Reference**: See `04-slash-commands.md` for all 28 commands and `05-workflow-scripts.md` for all phase scripts
