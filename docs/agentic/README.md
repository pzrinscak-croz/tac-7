# ADW Agentic Layer Documentation

Complete course material for understanding, operating, and extending the AI Developer Workflow (ADW) system.

## Quick Start

**New to ADW?** Start here:
1. **[00-overview.md](00-overview.md)** — What is ADW and how does it work?
2. **[01-getting-started.md](01-getting-started.md)** — Set up and run your first workflow
3. **[02-core-concepts.md](02-core-concepts.md)** — Understand the fundamental building blocks

## Complete Learning Path

| Document | Purpose | Duration | For Whom |
|----------|---------|----------|----------|
| **00-overview.md** | Architecture, design principles, end-to-end example | 15 min | Everyone |
| **01-getting-started.md** | Prerequisites, environment setup, first run | 20 min | Operators |
| **02-core-concepts.md** | ADW ID, state, worktrees, model sets, isolation | 25 min | Developers |
| **03-claude-code-layer.md** | Hooks, settings, permissions, MCP config | 20 min | Ops / Advanced users |
| **04-slash-commands.md** | Complete reference of all 28 commands | 30 min | Reference |
| **05-workflow-scripts.md** | All phase scripts, pipelines, orchestrators, modules | 40 min | Developers |
| **06-triggering.md** | How to start workflows (webhook, cron, CLI) | 25 min | Operators |
| **07-operations.md** | Monitoring, debugging, logs, maintenance | 25 min | Operators |
| **08-extending.md** | Adding commands, phases, hooks, pipelines | 30 min | Developers |

**Total learning time**: ~3.5 hours for comprehensive understanding

## By Role

### For Operators / DevOps

1. Read **01-getting-started.md** to set up the system
2. Read **06-triggering.md** to understand how to start workflows
3. Read **07-operations.md** for monitoring and troubleshooting
4. Keep **04-slash-commands.md** and **05-workflow-scripts.md** as reference

### For Developers / Engineers

1. Read **00-overview.md** for the big picture
2. Read **02-core-concepts.md** to understand the fundamentals
3. Read **05-workflow-scripts.md** to understand the code structure
4. Read **08-extending.md** when you want to add features
5. Use **04-slash-commands.md** as reference for command behavior

### For Architects / Tech Leads

1. Read **00-overview.md** and **02-core-concepts.md** first
2. Dive into **05-workflow-scripts.md** for implementation details
3. Review **03-claude-code-layer.md** for security model
4. Study **08-extending.md** to understand extensibility patterns

## Document Summaries

### [00-overview.md](00-overview.md)
Explains what ADW is and why it exists. Shows the architecture with ASCII diagrams, component map, design principles, and a complete end-to-end workflow example. **Start here if you're new.**

**Key topics**: Purpose, architecture, components, design principles, complete example

### [01-getting-started.md](01-getting-started.md)
Step-by-step setup guide. Prerequisites, environment configuration, first manual workflow, automated triggers setup, and troubleshooting. **Read this to get up and running.**

**Key topics**: Prerequisites, .env setup, first run, health check, webhook/cron setup, ZTE safety

### [02-core-concepts.md](02-core-concepts.md)
Deep dive into the fundamental concepts that make ADW work: ADW ID, state persistence, git worktrees, port management, model sets, slash commands, JSON schema, and a complete worked example.

**Key topics**: ADW ID, state file, worktrees, ports, model sets, slash commands, structured outputs

### [03-claude-code-layer.md](03-claude-code-layer.md)
How Claude Code is configured: permissions (allow/deny lists), 7 lifecycle hooks (pre_tool_use, post_tool_use, stop, etc.), settings files, MCP configuration, and security model.

**Key topics**: settings.json, hooks, security, MCP, Playwright config

### [04-slash-commands.md](04-slash-commands.md)
Complete reference of all 28 slash commands organized by category: planning (/feature, /bug, /chore, /patch), implementation (/implement), testing (/test, /test_e2e, /resolve_*), review (/review), documentation (/document, /track_agentic_kpis), git/VCS, classification, setup/infra, and human review.

**Key topics**: All command signatures, arguments, return values, when to use each

### [05-workflow-scripts.md](05-workflow-scripts.py)
All 13 phase scripts and their core modules: adw_plan_iso, adw_build_iso, adw_test_iso, adw_review_iso, adw_document_iso, adw_ship_iso (ZTE), plus pipeline orchestrators and core Python modules (agent.py, state.py, etc.).

**Key topics**: Phase flow, state lifecycle, SDLC vs ZTE, module responsibilities

### [06-triggering.md](06-triggering.md)
Four ways to start workflows: GitHub webhook (real-time, production-recommended), cron polling (fallback, every 20s), direct CLI (manual/scripting), and interactive Claude Code. Includes setup, security (loop prevention, ZTE uppercase requirement), and examples.

**Key topics**: Webhook setup, cron polling, CLI invocation, ZTE safety, model set selection

### [07-operations.md](07-operations.md)
Production operations: logging architecture (hooks logs + agent logs), reading logs, monitoring active workflows, debugging common failures, performance metrics (KPIs), worktree management, database management, port management, screenshot handling, and maintenance tasks.

**Key topics**: Log structure, monitoring, debugging, maintenance, cleanup, escalation

### [08-extending.md](08-extending.md)
How to extend ADW: add new slash commands (5 steps), new phases (5 steps), pipelines, hooks, custom environment variables, custom logging, custom triggers, and testing extensions. Includes best practices and documentation guidelines.

**Key topics**: Custom commands, custom phases, pipelines, hooks, testing, documentation

## Navigation

### By Task

**I want to...**

- **Set up ADW** → [01-getting-started.md](01-getting-started.md)
- **Understand how it works** → [00-overview.md](00-overview.md) + [02-core-concepts.md](02-core-concepts.md)
- **Find what a command does** → [04-slash-commands.md](04-slash-commands.md)
- **Understand the code** → [05-workflow-scripts.md](05-workflow-scripts.md)
- **Debug a problem** → [07-operations.md](07-operations.md)
- **Trigger a workflow** → [06-triggering.md](06-triggering.md)
- **Add a custom command** → [08-extending.md](08-extending.md)
- **Understand the security model** → [03-claude-code-layer.md](03-claude-code-layer.md)

### By Concept

- **ADW ID** → [02-core-concepts.md#adw-id](02-core-concepts.md#adw-id)
- **State** → [02-core-concepts.md#adw-state](02-core-concepts.md#adw-state)
- **Worktrees** → [02-core-concepts.md#git-worktrees](02-core-concepts.md#git-worktrees)
- **Ports** → [02-core-concepts.md#port-management](02-core-concepts.md#port-management)
- **Model Sets** → [02-core-concepts.md#model-sets](02-core-concepts.md#model-sets)
- **Slash Commands** → [04-slash-commands.md](04-slash-commands.md)
- **Phases** → [05-workflow-scripts.md#phase-scripts](05-workflow-scripts.md#phase-scripts)
- **Pipelines** → [05-workflow-scripts.md#pipeline-orchestrators](05-workflow-scripts.md#pipeline-orchestrators)
- **Webhooks** → [06-triggering.md#trigger-1-webhook](06-triggering.md#trigger-1-webhook)
- **Logs** → [07-operations.md#logging-architecture](07-operations.md#logging-architecture)

## Key Files Referenced

These are the important files in the project that the documentation discusses:

```
.claude/
├── settings.json              # Permissions + hook registration
├── settings.local.json        # MCP server config
├── commands/                  # 28 slash command prompt files
├── hooks/                     # 7 lifecycle hook scripts
└── README.md                  # ADW guide (brief)

adws/
├── adw_modules/
│   ├── agent.py              # Claude Code bridge
│   ├── state.py              # State management
│   ├── data_types.py         # Pydantic models
│   ├── workflow_ops.py        # Orchestration logic
│   └── ... (5 more modules)
├── adw_plan_iso.py           # Planning phase
├── adw_build_iso.py          # Build phase
├── adw_test_iso.py           # Test phase
├── adw_review_iso.py         # Review phase
├── adw_document_iso.py       # Documentation phase
├── adw_ship_iso.py           # Shipping phase (ZTE)
├── adw_sdlc_iso.py           # Full SDLC orchestrator
├── adw_sdlc_zte_iso.py       # ZTE (auto-merge) orchestrator
├── adw_triggers/
│   ├── trigger_webhook.py    # GitHub webhook entry point
│   └── trigger_cron.py       # Polling entry point
└── adw_tests/                # Test suite

specs/                         # Generated implementation plans
agents/                        # Runtime state + logs (created at startup)
logs/                          # Claude Code hook telemetry
app_docs/                      # Generated docs + KPI tracking
```

## Learning Resources

### Understanding the Codebase

```bash
# Get a quick orientation
/prime

# Understand git history
git log --oneline adws/ | head -20

# Understand what changed recently
git diff HEAD~5 adws/adw_modules/agent.py

# See an example run
cat agents/cc73faf1/adw_state.json | jq .
cat agents/cc73faf1/sdlc_planner/raw_output.jsonl | head -20
```

### Running Examples

```bash
# Health check
/health_check

# Manual workflow with first issue
uv run adws/adw_plan_iso.py 47

# Inspect the generated spec
cat specs/issue-47-adw-*/sdlc_planner-*.md | head -50

# See what state was created
cat agents/*/adw_state.json | jq '.adw_id'
```

### Asking for Help

When asking for help about ADW, reference specific documents:

> "Looking at 04-slash-commands.md, I don't understand how `/review` handles blockers. Can you explain?"

> "Per 05-workflow-scripts.md, the adw_sdlc_iso orchestrator stops on review failures. How does error handling work?"

## Version & Updates

**Last Updated**: March 24, 2026

**ADW Version**: ~1.0 (stable)

**Claude Code**: Haiku 4.5 (default), Sonnet 4.6, Opus 4.6

These docs cover the complete ADW system as of March 2026. Check `adws/README.md` for the latest code changes.

## Contributing to These Docs

When updating ADW, please update the corresponding document section:

- Adding a command? Update **04-slash-commands.md**
- Adding a phase? Update **05-workflow-scripts.md** and **08-extending.md**
- Changing hooks? Update **03-claude-code-layer.md**
- Adding operations guidance? Update **07-operations.md**

## Contact & Support

Questions about ADW? Check these resources in order:

1. **These docs** (most questions are answered here)
2. **[adws/README.md](../../adws/README.md)** (high-level technical overview)
3. **Issue comments** on GitHub (see what other team members asked)
4. **Ask a colleague** familiar with ADW
5. **Debug with Claude Code** (`claude -p "explain this log"`)
