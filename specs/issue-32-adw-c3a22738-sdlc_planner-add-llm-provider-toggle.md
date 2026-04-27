# Feature: LLM Provider Toggle

## Metadata
issue_number: `32`
adw_id: `c3a22738`
issue_json: `{"number":32,"title":"LLM Provider Toggle","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nA visible toggle/dropdown in the UI to switch between OpenAI and Anthropic. Currently the provider is hardcoded to 'openai' in main.ts:49. Let the user pick, persist the choice in localStorage.\n\nScope:\n\nClient: Add a select dropdown near the query button, send chosen provider in the existing llm_provider field\nServer: Already supports both providers -- no backend changes needed\nAcceptance criteria:\n\nA provider dropdown is visible near the query controls (not hidden in settings)\nSelecting \"Anthropic\" sends llm_provider: \"anthropic\" in the request\nSelecting \"OpenAI\" sends llm_provider: \"openai\" in the request\nThe selected provider persists across page reloads\nBoth providers return valid results when their API keys are configured"}`

## Feature Description
Add a visible LLM provider selector to the query controls so the user can choose between OpenAI and Anthropic before running a natural-language query. Currently the client always sends `llm_provider: "openai"` (hardcoded in `app/client/src/main.ts:49`), so users cannot influence which model service the backend routes to. This feature surfaces a `<select>` dropdown next to the Query button, threads the selection into the `/api/query` request body, and persists the user's choice in `localStorage` so it survives page reloads.

The backend already supports both providers via the `llm_provider: Literal["openai", "anthropic"]` field on `QueryRequest` (`app/server/core/data_models.py:20`) — no server changes are required.

## User Story
As a user of the Natural Language SQL Interface
I want to choose which LLM provider (OpenAI or Anthropic) handles my query
So that I can compare results, fall back to whichever key I have configured, and have my preference remembered between sessions.

## Problem Statement
The client hardcodes `llm_provider: 'openai'` when calling `POST /api/query`. Users cannot choose Anthropic from the UI, even though the backend's `generate_sql` router accepts the `llm_provider` field and the application supports both providers. There is also no mechanism to remember the user's preferred provider across reloads.

## Solution Statement
Introduce a `<select>` element labeled "Provider" with two options ("OpenAI", "Anthropic") inside the existing `.query-controls-left` group in `app/client/index.html`. In `app/client/src/main.ts`:

1. On `DOMContentLoaded`, read the saved provider from `localStorage` (key: `llm_provider`) — default to `"openai"` when absent or invalid.
2. Apply the saved value to the dropdown.
3. On `change`, write the new value back to `localStorage`.
4. Replace the hardcoded `llm_provider: 'openai'` in `executeQuery` with a read of the dropdown's current value.

Add minimal CSS so the dropdown sits inline with the existing buttons and matches the surface styling. Cover the new behavior with an E2E Playwright test that verifies the dropdown is visible, persists across reload, and that the selection is reflected in the network payload.

## Relevant Files
Use these files to implement the feature:

- `app/client/index.html` — Contains the `.query-controls-left` group at lines 22-29 where the provider dropdown must be inserted next to the Query and Upload buttons.
- `app/client/src/main.ts` — Hosts `initializeQueryInput()` (lines 21-91); contains the hardcoded `llm_provider: 'openai'` at line 49 that must be replaced with the dropdown's current value, and is where the `localStorage` load/save wiring goes (alongside or inside a new `initializeProviderSelector()` helper invoked from the `DOMContentLoaded` handler at lines 7-13).
- `app/client/src/types.d.ts` — Defines `QueryRequest` (lines 13-17) with `llm_provider: "openai" | "anthropic"`. Use this union for the dropdown's typed value; no schema change required.
- `app/client/src/style.css` — Holds the `.query-controls` and `.query-controls-left` rules (around lines 88-98) that the new selector must align with visually.
- `app/server/core/data_models.py` — Confirms the backend already accepts `llm_provider` on `QueryRequest`. Read-only; no changes.
- `app/server/core/llm_processor.py` — `generate_sql()` (lines 267-285) shows the existing routing logic. Read-only; no changes (see Notes for a behavioral nuance worth being aware of).
- `app/client/src/api/client.ts` — Already forwards `QueryRequest` verbatim to `/api/query` via `api.processQuery` (lines 49-57). Read-only; no changes.
- `.claude/commands/test_e2e.md` — Read this to understand how E2E tests are executed via the Playwright MCP and how screenshots are organized; needed to author the new test file correctly.
- `.claude/commands/e2e/test_basic_query.md` — Reference for the test-file format (User Story, Test Steps, Success Criteria) used when authoring the new E2E test file.
- `app_docs/feature-4c768184-model-upgrades.md` — Conditional doc covering OpenAI/Anthropic model configurations in `llm_processor`; useful background when verifying both providers still return valid results.

### New Files

- `specs/issue-32-adw-c3a22738-sdlc_planner-add-llm-provider-toggle.md` — This plan (already being created).
- `.claude/commands/e2e/test_llm_provider_toggle.md` — New E2E test file validating the dropdown is visible, the selection round-trips through `localStorage`, and a query executes successfully with the chosen provider.

## Implementation Plan
### Phase 1: Foundation
Add the markup and storage helper. This is the smallest change set that lets the rest of the feature compose cleanly: a `<select id="llm-provider-select">` inside `.query-controls-left` with two `<option>` elements, plus a small `getStoredProvider()` / `setStoredProvider()` pair in `main.ts` that reads/writes the `llm_provider` key in `localStorage` and validates the value against the `"openai" | "anthropic"` union (defaulting to `"openai"` on anything else).

### Phase 2: Core Implementation
Wire the dropdown into the query flow. Add an `initializeProviderSelector()` function (called from the existing `DOMContentLoaded` handler) that hydrates the `<select>` with the stored value and attaches a `change` listener that persists the new value. Replace the hardcoded `llm_provider: 'openai'` in `executeQuery` with a read of the `<select>`'s current value. Add minimal CSS so the dropdown is vertically aligned with the surrounding buttons and respects the existing color tokens (`--border-color`, `--surface`, `--text-primary`).

### Phase 3: Integration
Author the new E2E test (`.claude/commands/e2e/test_llm_provider_toggle.md`) covering: dropdown visibility, default value, persistence across reload, and a successful query round-trip with each provider value selected. Run the full validation suite (server pytest, client `tsc --noEmit`, client `bun run build`, and the new E2E test) to confirm no regressions in the existing query, upload, random-query, export, or debounce flows.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Add the provider dropdown markup
- In `app/client/index.html`, inside `.query-controls-left` (currently containing the Query and Upload buttons at lines 23-26), append a new `<select id="llm-provider-select" aria-label="LLM Provider">` element with two `<option>` children: `value="openai"` (label "OpenAI") and `value="anthropic"` (label "Anthropic").
- Place the `<select>` after the Upload button so the visual order is: Query · Upload · Provider dropdown.
- Do not change the IDs or classes of the existing buttons.

### Step 2: Style the dropdown to match the existing controls
- In `app/client/src/style.css`, add a rule for `#llm-provider-select` that gives it: padding consistent with the secondary button (e.g. `0.5rem 0.75rem`), the existing `--border-color` 1-2px border, `border-radius: 8px`, `background: var(--surface)`, `color: var(--text-primary)`, and `font-family: inherit`.
- Verify that `.query-controls-left` (already `display: flex; gap: 1rem;` at lines 95-98) lays the dropdown out inline with the buttons without extra adjustments. Add only what is necessary.

### Step 3: Add a typed provider-storage helper in main.ts
- In `app/client/src/main.ts`, add two small helpers near the top (after the imports / before `initializeQueryInput`):
  - `getStoredProvider(): QueryRequest["llm_provider"]` — reads `localStorage.getItem('llm_provider')`, returns `'openai'` or `'anthropic'` if matched, otherwise returns `'openai'`.
  - `setStoredProvider(value: QueryRequest["llm_provider"]): void` — writes the value to `localStorage` under the key `llm_provider`.
- Use the literal union from `QueryRequest` in `types.d.ts` so TypeScript enforces correctness.

### Step 4: Add and call `initializeProviderSelector`
- Add a new function `initializeProviderSelector()` in `main.ts` that:
  - Looks up `document.getElementById('llm-provider-select') as HTMLSelectElement`.
  - Sets `select.value = getStoredProvider()` to hydrate from storage.
  - Attaches a `change` listener that calls `setStoredProvider(select.value as QueryRequest["llm_provider"])`.
- Call `initializeProviderSelector()` inside the existing `DOMContentLoaded` handler (lines 7-13), before `loadDatabaseSchema()`.

### Step 5: Use the selected provider in `executeQuery`
- In `executeQuery` (inside `initializeQueryInput`), replace the hardcoded `llm_provider: 'openai'` at line 49 with a value read from the dropdown: `(document.getElementById('llm-provider-select') as HTMLSelectElement).value as QueryRequest["llm_provider"]`.
- Keep the rest of the request body and the disabled/loading UI flow unchanged.

### Step 6: Create the E2E test file
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to confirm the format (User Story, Test Steps, Success Criteria, screenshot conventions).
- Create `.claude/commands/e2e/test_llm_provider_toggle.md` with:
  - **User Story**: As a user, I want to pick the LLM provider in the UI and have my choice remembered, so I can switch between OpenAI and Anthropic without code changes.
  - **Test Steps** (minimal but specific):
    1. Navigate to the application URL.
    2. Take a screenshot of the initial state.
    3. **Verify** the provider dropdown (`#llm-provider-select`) is visible in the query controls and defaults to `OpenAI`.
    4. Upload sample users data (click Upload → Users Data sample) so a queryable table exists.
    5. Change the dropdown to `Anthropic`. Take a screenshot.
    6. Reload the page.
    7. **Verify** the dropdown still shows `Anthropic` after reload (persistence). Take a screenshot.
    8. Enter the query "Show me all users from the users table" and click Query.
    9. **Verify** results appear and SQL is displayed without errors. Take a screenshot.
    10. Switch the dropdown back to `OpenAI`, run the same query.
    11. **Verify** results appear without errors. Take a screenshot.
  - **Success Criteria**: Dropdown is visible, defaults to OpenAI, persists Anthropic across reload, both providers complete a query without error, 5 screenshots are saved.

### Step 7: Manual smoke test in the browser
- Start the app via `./scripts/start.sh` (or follow the manual start in README).
- Open the frontend, confirm the dropdown is rendered next to Query and Upload, switch values, reload, run a query for each provider with a sample table loaded. Open DevTools → Network and confirm the `/api/query` request body's `llm_provider` field matches the dropdown's value.

### Step 8: Run validation commands
- Execute every command listed in the **Validation Commands** section below; all must pass with zero regressions.

## Testing Strategy
### Unit Tests
- No backend changes, so no new server-side unit tests are required. Existing `app/server/tests/` suites must still pass.
- The client codebase does not currently host unit tests (the project relies on TypeScript type-checking + E2E coverage), so do not introduce a unit-test framework for this small change. Coverage comes from the new E2E test plus existing E2E tests that exercise `executeQuery` (e.g. `test_basic_query`, `test_complex_query`, `test_disable_input_debounce`).

### Edge Cases
- `localStorage.getItem('llm_provider')` returns `null` (first visit) → default to `"openai"`.
- `localStorage.getItem('llm_provider')` returns an unexpected string (e.g. `"gemini"` from a tampered value) → fall back to `"openai"` and do not crash.
- User runs multiple queries in quick succession after toggling the dropdown — the existing debounce in `initializeQueryInput` (lines 27-83) must still serialize them with the chosen provider; covered indirectly by `test_disable_input_debounce`.
- Only one of `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` is set in the server environment: backend may still route based on key availability (see Notes); the dropdown should still persist and the request body should still carry the user's choice. Document this in the test that both providers "return valid results when their API keys are configured" — the test environment must have both keys for the full check, otherwise verify request payload only.
- Pre-existing UI flows (Upload, Generate Random Query, Export, table removal) must be untouched.

## Acceptance Criteria
- A `<select>` labeled "Provider" with options "OpenAI" and "Anthropic" is visible inside `.query-controls-left`, next to the Query and Upload buttons (not hidden behind a settings panel or modal).
- Selecting "Anthropic" causes the next `POST /api/query` request to include `"llm_provider": "anthropic"` in the JSON body.
- Selecting "OpenAI" causes the next `POST /api/query` request to include `"llm_provider": "openai"` in the JSON body.
- The selected provider persists across a full page reload (verified via `localStorage` and the dropdown's `value` after refresh).
- With valid API keys configured for both providers in the server environment, queries succeed end-to-end with either selection (results and SQL render without error in the UI).
- All existing E2E tests continue to pass; `cd app/server && uv run pytest` passes; `cd app/client && bun tsc --noEmit` passes; `cd app/client && bun run build` succeeds.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` — Run server tests to confirm no backend regressions (no backend code changed; this is a safety check).
- `cd app/client && bun tsc --noEmit` — Type-check the client to catch any breakage from the dropdown wiring and `localStorage` helpers.
- `cd app/client && bun run build` — Production build of the client to confirm no build errors after the HTML/TS/CSS edits.
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_llm_provider_toggle.md` via the Playwright MCP to validate the dropdown is visible, persists across reload, and that queries succeed under both provider selections.
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_basic_query.md` to confirm the existing default-OpenAI query path still works (regression check).

## Notes
- **No new dependencies.** The feature uses only the browser `localStorage` API and existing types — `uv add` / `bun add` are not required.
- **No backend changes.** `core/data_models.py:20` already accepts `llm_provider: Literal["openai", "anthropic"]`, and `core/llm_processor.py:267-285` already routes to the appropriate generator.
- **Subtle backend routing nuance (informational, do not change):** `generate_sql()` in `llm_processor.py` currently prioritizes API-key availability over `request.llm_provider`. Specifically, if `OPENAI_API_KEY` is set, it routes to OpenAI regardless of the request's `llm_provider`, and only consults the request preference when both keys are present in the fall-through branch. In practice — for environments where only one key is configured — the user's selection has no functional effect; the dropdown's persistence and payload behavior still satisfy the issue's acceptance criteria as written ("Server: Already supports both providers -- no backend changes needed"). If, during validation, the team wants the dropdown to actually steer routing when both keys are set, that's a separate follow-up to invert the priority in `generate_sql()` (consult `request.llm_provider` first, then fall back to whatever key is available). Flag this in the PR description rather than expanding scope here.
- **Accessibility.** Add an `aria-label="LLM Provider"` to the `<select>` so screen-reader users get a meaningful name without requiring a visible `<label>`. If the team prefers a visible label, a small `<label for="llm-provider-select">Provider</label>` placed immediately before the select is also acceptable and keeps layout simple.
- **Future extensibility.** Adding a third provider (e.g. Gemini) in the future would require: a new `<option>`, an extension to the `Literal["openai" | "anthropic"]` union in both `types.d.ts` and `data_models.py`, and a new generator branch in `llm_processor.py`. No design refactor needed.
