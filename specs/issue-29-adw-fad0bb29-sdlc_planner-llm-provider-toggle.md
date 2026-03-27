# Feature: LLM Provider Toggle

## Metadata
issue_number: `fad0bb29`
adw_id: `29`
issue_json: ``

## Feature Description
Add a visible dropdown in the UI that allows users to switch between OpenAI and Anthropic as the LLM provider for natural language query processing. Currently the provider is hardcoded to `'openai'` in `main.ts:49`. The dropdown will appear near the query controls, send the chosen provider in the existing `llm_provider` field, and persist the user's choice in localStorage across page reloads. The server already supports both providers — this is a client-only change.

## User Story
As a user of the Natural Language SQL Interface
I want to choose between OpenAI and Anthropic as my LLM provider
So that I can use my preferred AI model for generating SQL queries

## Problem Statement
The LLM provider is hardcoded to OpenAI on the client side, even though the server supports both OpenAI and Anthropic. Users with Anthropic API keys configured cannot leverage Anthropic from the UI, and there is no way to compare results between providers without modifying source code.

## Solution Statement
Add a `<select>` dropdown to the query controls area (next to the Query and Upload buttons) that lets users pick "OpenAI" or "Anthropic". The selected value is stored in localStorage and read on page load. When a query is submitted, the selected provider is sent as `llm_provider` in the request payload instead of the hardcoded `'openai'` string. No backend changes are required.

## Relevant Files
Use these files to implement the feature:

- `app/client/index.html` — Add the provider `<select>` dropdown element to the `.query-controls-left` div, next to the existing Query and Upload buttons
- `app/client/src/main.ts` — Initialize the dropdown from localStorage, replace the hardcoded `llm_provider: 'openai'` on line 49 with the dropdown's current value
- `app/client/src/style.css` — Add styling for the provider dropdown to match existing controls (read this file for existing CSS variables and patterns)
- `app/client/src/types.d.ts` — Reference only; the `QueryRequest` interface already has `llm_provider: "openai" | "anthropic"` — no changes needed
- `app/client/src/api/client.ts` — Reference only; the `processQuery` method already passes the full request object — no changes needed
- `app/server/core/data_models.py` — Reference only; backend `QueryRequest` already accepts `llm_provider` — no changes needed
- `app/server/core/llm_processor.py` — Reference only; `generate_sql` already routes based on `llm_provider` — no changes needed
- `app_docs/feature-4c768184-model-upgrades.md` — Context on current model configurations (relevant since we're working with the llm_processor module)
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand how to create an E2E test file

### New Files
- `.claude/commands/e2e/test_llm_provider_toggle.md` — E2E test to validate provider toggle functionality

## Implementation Plan
### Phase 1: Foundation
Add the HTML select element to the query controls area and basic CSS styling. This establishes the UI element that the rest of the feature depends on.

### Phase 2: Core Implementation
Wire up the dropdown to localStorage for persistence and replace the hardcoded `llm_provider` value in `main.ts` with the dropdown's selected value. This is the core behavior change.

### Phase 3: Integration
Create the E2E test to validate the full flow, then run all validation commands to ensure zero regressions.

## Step by Step Tasks

### Step 1: Add provider dropdown to HTML
- In `app/client/index.html`, add a `<select>` element with `id="llm-provider-select"` inside the `.query-controls-left` div, after the Upload button
- Add two `<option>` elements: `<option value="openai">OpenAI</option>` and `<option value="anthropic">Anthropic</option>`
- Default selected option should be `openai`

### Step 2: Style the provider dropdown
- In `app/client/src/style.css`, add styles for `#llm-provider-select` that match the existing button styles (use the same `--primary-color`, `--surface`, `--border-color` variables, similar padding/border-radius)
- Ensure the dropdown aligns properly within the `.query-controls-left` flex container

### Step 3: Wire up localStorage persistence and request payload
- In `app/client/src/main.ts`, at the top of `initializeQueryInput()`:
  - Read the saved provider from `localStorage.getItem('llm_provider')` (default to `'openai'` if not set)
  - Set the dropdown's value to the saved provider
  - Add a `change` event listener on the dropdown that saves the new value to `localStorage.setItem('llm_provider', value)`
- Replace line 49 (`llm_provider: 'openai'`) with `llm_provider: (document.getElementById('llm-provider-select') as HTMLSelectElement).value as 'openai' | 'anthropic'`

### Step 4: Create E2E test file
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand the E2E test format
- Create `.claude/commands/e2e/test_llm_provider_toggle.md` with tests that:
  1. Navigate to the application
  2. Verify the provider dropdown is visible near the query controls
  3. Verify default selection is "OpenAI"
  4. Take a screenshot of initial state showing the dropdown
  5. Select "Anthropic" from the dropdown
  6. Enter a query and click Query
  7. Verify the query executes successfully (results appear)
  8. Take a screenshot showing results with Anthropic selected
  9. Reload the page
  10. Verify the dropdown still shows "Anthropic" (localStorage persistence)
  11. Take a screenshot confirming persistence
  12. Select "OpenAI", enter a query, click Query
  13. Verify the query executes successfully
  14. Take a final screenshot

### Step 5: Run validation commands
- Execute all validation commands below to confirm zero regressions

## Testing Strategy
### Unit Tests
- No new unit tests required — the server-side logic is unchanged and already tested
- TypeScript type checking (`bun tsc --noEmit`) validates that the provider value is correctly typed

### Edge Cases
- localStorage is empty (first visit) — should default to OpenAI
- localStorage contains an invalid value — should default to OpenAI
- User switches provider mid-session — next query should use the new provider
- Page reload preserves the selected provider

## Acceptance Criteria
1. A provider dropdown is visible near the query controls (not hidden in settings)
2. Selecting "Anthropic" sends `llm_provider: "anthropic"` in the request
3. Selecting "OpenAI" sends `llm_provider: "openai"` in the request
4. The selected provider persists across page reloads via localStorage
5. Both providers return valid results when their API keys are configured
6. The dropdown styling is consistent with existing UI controls
7. All existing tests pass with zero regressions

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate zero regressions
- `cd app/client && bun tsc --noEmit` - Run TypeScript type checking to validate no type errors
- `cd app/client && bun run build` - Run frontend build to validate no build errors
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_llm_provider_toggle.md` E2E test to validate the provider toggle works end-to-end

## Notes
- The server's `generate_sql` function in `llm_processor.py` has its own routing logic that prioritizes API key availability over the `llm_provider` request field. If only one API key is configured, the server will use that provider regardless of what the client sends. This is expected server behavior and not something the client should change.
- The `generate_random_query` endpoint does not accept an `llm_provider` parameter — it uses its own key-availability-based routing. Extending it to respect the toggle is out of scope for this feature.
- No new libraries or dependencies are needed.
