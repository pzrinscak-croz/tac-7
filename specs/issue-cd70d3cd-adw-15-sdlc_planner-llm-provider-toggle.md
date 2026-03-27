# Feature: LLM Provider Toggle

## Metadata
issue_number: `cd70d3cd`
adw_id: `15`
issue_json: `{"number":15,"title":"LLM Provider Toggle","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set base\n\nA visible toggle/dropdown in the UI to switch between OpenAI and Anthropic. Currently the provider is hardcoded to `'openai'` in `main.ts:49`. Let the user pick, persist the choice in localStorage.\n\n**Scope:**\n- Client: Add a select dropdown near the query button, send chosen provider in the existing `llm_provider` field\n- Server: Already supports both providers -- no backend changes needed\n\n**Acceptance criteria:**\n1. A provider dropdown is visible near the query controls (not hidden in settings)\n2. Selecting \"Anthropic\" sends `llm_provider: \"anthropic\"` in the request\n3. Selecting \"OpenAI\" sends `llm_provider: \"openai\"` in the request\n4. The selected provider persists across page reloads\n5. Both providers return valid results when their API keys are configured"}`

## Feature Description
Add a visible provider selector dropdown to the query controls area of the UI, allowing users to switch between OpenAI and Anthropic as their LLM provider. The selected provider is persisted in localStorage so the user's preference survives page reloads. The chosen provider is sent in the existing `llm_provider` field of every query request. The server already supports both providers — only client-side changes are required.

## User Story
As a user of the Natural Language SQL Interface
I want to select which LLM provider (OpenAI or Anthropic) processes my queries
So that I can use the provider I prefer or whose API key I have configured

## Problem Statement
The LLM provider is hardcoded to `'openai'` on line 49 of `main.ts`. Users who have only an Anthropic API key configured, or who prefer Anthropic's models, cannot use the application as intended without modifying source code. There is no UI mechanism to choose the provider at runtime.

## Solution Statement
Add a `<select>` dropdown element to the `.query-controls` section in `index.html`, positioned next to the query button. On page load, read the saved provider from `localStorage` (defaulting to `'openai'`). When the user changes the dropdown, persist the new value to `localStorage`. When a query is submitted, read the current dropdown value and pass it as `llm_provider` in the `processQuery` call — replacing the hardcoded `'openai'` string. Style the dropdown to match the existing secondary-button aesthetic.

## Relevant Files
Use these files to implement the feature:

- `app/client/index.html` — HTML structure; the `<select>` dropdown is added here inside `.query-controls`
- `app/client/src/main.ts` — Main TypeScript entry point; replace the hardcoded `llm_provider: 'openai'` (line 49) with a live read of the dropdown value; add localStorage init and change-listener logic
- `app/client/src/style.css` — Add styling for the provider `<select>` element so it matches the existing button aesthetic; read this file to follow existing CSS conventions (`app/client/src/style.css` should be read per conditional_docs.md because we are making style changes)
- `app/client/src/types.d.ts` — Already defines `llm_provider: "openai" | "anthropic"` in `QueryRequest`; no changes required but read for reference
- `app/client/src/api/client.ts` — Already accepts `llm_provider` in `processQuery`; no changes required but read for reference
- `app_docs/feature-4c768184-model-upgrades.md` — Documents existing LLM provider support on the server; confirms no backend changes are needed
- `.claude/commands/test_e2e.md` — Read to understand how to create and execute E2E tests
- `.claude/commands/e2e/test_basic_query.md` — Reference example for E2E test file format

### New Files
- `.claude/commands/e2e/test_llm_provider_toggle.md` — New E2E test file that validates the provider dropdown is visible, persists across reloads, and sends the correct provider in requests

## Implementation Plan
### Phase 1: Foundation
Read the relevant client files (`index.html`, `main.ts`, `style.css`, `types.d.ts`, `api/client.ts`) to fully understand existing patterns, HTML structure, CSS conventions, and how `processQuery` is called before making any changes.

### Phase 2: Core Implementation
1. Add the `<select id="provider-select">` element with `<option>` values for `openai` and `anthropic` inside `.query-controls` in `index.html`
2. In `main.ts`, add an `initializeProviderSelect()` function that:
   - Reads the saved value from `localStorage` key `llm_provider` (default `'openai'`)
   - Sets the dropdown's selected value on page load
   - Listens for `change` events and writes the new value to `localStorage`
3. Replace the hardcoded `llm_provider: 'openai'` in the `processQuery` call with a live read of the dropdown element's current value
4. Call `initializeProviderSelect()` at app startup alongside the other `initialize*` calls
5. Add CSS in `style.css` to style the `<select>` element to visually match the existing secondary buttons

### Phase 3: Integration
Create the E2E test file, then run all validation commands to confirm zero regressions and that the dropdown persists across reloads.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Read relevant files
- Read `app/client/index.html` to understand the current HTML structure and the `.query-controls` section
- Read `app/client/src/main.ts` to understand the full file, especially the `initializeQueryInput` function and the hardcoded `llm_provider: 'openai'` at line 49
- Read `app/client/src/style.css` to understand existing CSS patterns, variables, and button styles
- Read `app/client/src/types.d.ts` and `app/client/src/api/client.ts` for reference

### Step 2: Create the E2E test file
- Create `.claude/commands/e2e/test_llm_provider_toggle.md` following the format of `test_basic_query.md` and `test_complex_query.md`
- The test should:
  1. Navigate to the Application URL
  2. Take a screenshot of the initial state showing the provider dropdown is visible
  3. Verify the provider `<select>` element is present in the query controls
  4. Verify the default selected value is "OpenAI"
  5. Change the dropdown to "Anthropic"
  6. Take a screenshot showing the dropdown set to Anthropic
  7. Enter a simple query and click Query
  8. Verify results appear (confirming Anthropic provider returns results)
  9. Take a screenshot of the results
  10. Reload the page
  11. Verify the dropdown still shows "Anthropic" (localStorage persistence)
  12. Take a screenshot confirming persistence after reload
- Success criteria: dropdown visible, defaults to OpenAI, persists across reload, query succeeds with Anthropic selected; 4 screenshots taken

### Step 3: Add provider dropdown to HTML
- Edit `app/client/index.html` — add a `<select id="provider-select">` element inside `.query-controls`, placed after the Query button and before the Upload button:
  ```html
  <select id="provider-select" class="provider-select">
    <option value="openai">OpenAI</option>
    <option value="anthropic">Anthropic</option>
  </select>
  ```

### Step 4: Style the provider dropdown
- Edit `app/client/src/style.css` — add CSS for `#provider-select` / `.provider-select` that matches the height, border-radius, font-size, and color scheme of the existing secondary buttons; follow the existing CSS variable conventions in the file

### Step 5: Update main.ts — add initializeProviderSelect
- Edit `app/client/src/main.ts`:
  - Add a new function `initializeProviderSelect()` that:
    - Gets the `<select id="provider-select">` element
    - Reads `localStorage.getItem('llm_provider')` (defaulting to `'openai'`)
    - Sets `selectEl.value` to the saved value on load
    - Adds a `change` event listener that calls `localStorage.setItem('llm_provider', selectEl.value)` on change
  - Call `initializeProviderSelect()` in the app startup section alongside other `initialize*` calls

### Step 6: Replace hardcoded llm_provider in processQuery call
- Edit `app/client/src/main.ts` line 49:
  - Replace `llm_provider: 'openai'` with `llm_provider: (document.getElementById('provider-select') as HTMLSelectElement).value as 'openai' | 'anthropic'`

### Step 7: Run validation commands
- Execute every command listed in the Validation Commands section and confirm all pass with zero errors

## Testing Strategy
### Unit Tests
No new unit tests are required — the change is purely client-side UI state management with no new logic that warrants isolation testing. The existing server-side pytest suite remains the server validation layer.

### Edge Cases
- **No localStorage entry on first visit**: dropdown must default to `'openai'`
- **Corrupt/unexpected localStorage value**: the dropdown's native behavior will show the first option (`openai`) if the stored value doesn't match any option
- **Query submitted while provider changes**: the value is read at submit time so there is no race condition
- **Server missing one API key**: the server already handles this; the client has no special handling needed

## Acceptance Criteria
1. A provider `<select>` dropdown is visible in the query controls area (not hidden in settings or any modal)
2. The dropdown defaults to "OpenAI" on first load when no localStorage entry exists
3. Selecting "Anthropic" from the dropdown causes subsequent queries to include `llm_provider: "anthropic"` in the request body
4. Selecting "OpenAI" from the dropdown causes subsequent queries to include `llm_provider: "openai"` in the request body
5. After changing the provider and reloading the page, the dropdown retains the previously selected provider (persisted via localStorage key `llm_provider`)
6. The dropdown is styled consistently with the existing query controls (height, font, border-radius)
7. No regressions in existing server tests (`uv run pytest` passes)
8. TypeScript compilation succeeds (`bun tsc --noEmit` passes)
9. Frontend build succeeds (`bun run build` passes)

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_llm_provider_toggle.md` to validate the provider toggle functionality end-to-end
- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` - Run TypeScript type checking to validate no type errors
- `cd app/client && bun run build` - Run frontend build to validate the feature compiles with zero errors

## Notes
- No backend changes are required; the server already accepts and routes `llm_provider: "openai" | "anthropic"` in the query request
- The `localStorage` key is `llm_provider` to match the field name used in the API request, keeping naming consistent
- The `<select>` element should be added between the Query button and Upload button per the design intent of "near the query button"
- See `app_docs/feature-4c768184-model-upgrades.md` for the current model versions used by each provider (Claude Sonnet 4 for Anthropic, GPT-4.1 for OpenAI)
- Both provider API keys must be present in the server environment for both options to return valid results; if only one key is configured, selecting the other will produce a server-side error
