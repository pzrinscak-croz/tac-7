# Feature: Increase Drop Zone Surface Area

## Metadata
issue_number: `1`
adw_id: `b5facb99`
issue_json: `{"number":1,"title":"Increase drop zone surface area","body":"/feature\n\nadw_sdlc_iso\n\nlets increase the drop zone surface area. instead of having to click \"upload data\". The user can drag and drop right on to the upper div or lower\ndiv and the ui will update to a 'drop to create table' text. This runs the same usual functionality but enhances the ui to be more user friendly."}`

## Feature Description
Extend drag-and-drop file upload functionality beyond the upload modal's internal drop zone. Users will be able to drag files directly onto the upper section (query input area, `#query-section`) or the lower section (available tables area, `#tables-section`) of the main page. When a file is dragged over either section, the UI updates to show a "Drop to create table" overlay, giving clear visual feedback. On drop, the file is processed using the existing `handleFileUpload` function — no modal required. This eliminates the extra step of clicking "Upload" to open the modal before dropping a file.

## User Story
As a data analyst
I want to drag and drop files directly onto the main page sections
So that I can upload data without navigating through the upload modal

## Problem Statement
Currently, users must click the "Upload" button to open a modal before they can use drag-and-drop file upload. The drag-and-drop target is hidden inside the modal, making the workflow unnecessarily multi-step and obscuring a common action.

## Solution Statement
Add drag event listeners to both the `#query-section` (upper div) and `#tables-section` (lower div). When a file is dragged over either section, display a full-section overlay with "Drop to create table" text. On drop, call the existing `handleFileUpload` function. This reuses all existing upload logic while making the drop target the entire visible page.

## Relevant Files
Use these files to implement the feature:

- `app/client/index.html` — Contains the `#query-section` and `#tables-section` divs that will become extended drop zones; overlay elements will be injected here or dynamically
- `app/client/src/main.ts` — Contains `initializeFileUpload()`, `handleFileUpload()`, and `initializeModal()` — the new drag listeners will be added in a new `initializePageDropZones()` function called from `DOMContentLoaded`
- `app/client/src/style.css` — Contains existing `.drop-zone` and `.drop-zone.dragover` styles; new CSS classes for page-level drop zone overlays will be added here

Read `app/client/src/style.css` to understand existing CSS variables and patterns before adding new styles.

Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand how to create an E2E test file.

### New Files
- `.claude/commands/e2e/test_drop_zone_area.md` — E2E test validating drag-and-drop on the upper and lower divs shows overlay and triggers upload

## Implementation Plan
### Phase 1: Foundation
Add CSS overlay classes for the drag-active state on page-level sections. These overlay styles will cover the section with a semi-transparent highlight and centered "Drop to create table" text, following the existing `.drop-zone.dragover` visual language.

### Phase 2: Core Implementation
Add a new `initializePageDropZones()` function in `main.ts` that:
1. Attaches `dragover`, `dragleave`, and `drop` event listeners to `#query-section` and `#tables-section`
2. On `dragover`: adds a CSS class (`section-dragover`) to the target section and shows a "Drop to create table" overlay
3. On `dragleave`: removes the class and hides the overlay (handling child element re-entry with `relatedTarget` check)
4. On `drop`: removes the class, hides the overlay, and calls `handleFileUpload(file)`

### Phase 3: Integration
Call `initializePageDropZones()` from the `DOMContentLoaded` handler alongside existing initializers. Verify the existing modal drop zone still works independently. Verify `handleFileUpload` closes the modal if open and shows the success message normally.

## Step by Step Tasks

### Step 1: Create E2E test file
- Create `.claude/commands/e2e/test_drop_zone_area.md` with steps to:
  - Navigate to the app
  - Take screenshot of initial state
  - Simulate drag-over on `#query-section` and verify the "Drop to create table" overlay appears
  - Take screenshot of drag-over state on upper section
  - Simulate drag-over on `#tables-section` and verify the overlay appears there
  - Take screenshot of drag-over state on lower section
  - Drop a sample `.csv` file on `#query-section` and verify the table is created (success message appears, tables list updates)
  - Take screenshot of success state

### Step 2: Add CSS for page-level drop zone overlays
- In `app/client/src/style.css`, add:
  - `.section-drop-target` — `position: relative` applied to sections acting as drop zones (already have it or add)
  - `.section-dragover` — visual highlight on the section (border or background change using existing CSS variables)
  - `.section-drop-overlay` — `position: absolute; inset: 0` overlay div with flex-centered "Drop to create table" text, semi-transparent background using `var(--primary-color)` at low opacity, high `z-index`, `pointer-events: none`, `border-radius` matching the section
  - `.section-drop-overlay.visible` — `display: flex` to show the overlay (default `display: none`)

### Step 3: Add overlay elements to HTML sections
- In `app/client/index.html`:
  - Add `class="section-drop-target"` to `#query-section` and `#tables-section` (or handle via JS)
  - Inject a `<div class="section-drop-overlay"><p>Drop to create table</p></div>` inside each section, or create them dynamically in JS

### Step 4: Implement `initializePageDropZones()` in main.ts
- Add a new function `initializePageDropZones()` in `app/client/src/main.ts`
- Target `#query-section` and `#tables-section`
- For each section:
  - On `dragover` (e.preventDefault(), check `e.dataTransfer.types` contains `Files`): add `section-dragover` class, show overlay
  - On `dragleave` (check `relatedTarget` is not inside the section to avoid flicker): remove class, hide overlay
  - On `drop` (e.preventDefault()): remove class, hide overlay, extract file from `e.dataTransfer.files[0]`, call `handleFileUpload(file)`
- Call `initializePageDropZones()` from the `DOMContentLoaded` handler in `main.ts`

### Step 5: Run Validation Commands
- Execute all validation commands listed in the Validation Commands section

## Testing Strategy
### Unit Tests
No new unit tests needed — the upload logic is unchanged. All behavior delegates to the existing `handleFileUpload` function.

### Edge Cases
- Dragging a non-file item (e.g., text) over the sections — should not show overlay (check `e.dataTransfer.types` includes `Files`)
- `dragleave` firing when moving between child elements — use `relatedTarget` check to avoid premature overlay removal
- Dragging over the modal while it's open — modal is `position: fixed` with `z-index: 1000`, so page sections are underneath; no conflict
- Dropping multiple files — only the first file (`files[0]`) is processed, matching existing behavior
- Dropping an unsupported file type — `handleFileUpload` / server returns an error, which `displayError` handles as before

## Acceptance Criteria
- Dragging a `.csv`, `.json`, or `.jsonl` file over `#query-section` shows a "Drop to create table" overlay on that section
- Dragging a `.csv`, `.json`, or `.jsonl` file over `#tables-section` shows a "Drop to create table" overlay on that section
- Dropping a file on either section triggers the upload and creates a table without opening the modal
- The success message appears after a successful drop upload, identical to the modal upload flow
- Moving the cursor away from a section (without dropping) hides the overlay and restores normal appearance
- The existing modal drop zone continues to work unchanged
- No TypeScript compilation errors (`bun tsc --noEmit` passes)
- Frontend builds successfully (`bun run build` passes)

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_drop_zone_area.md` to validate drag-and-drop on upper/lower sections works end-to-end
- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` - Run frontend type checks to validate the feature works with zero regressions
- `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions

## Notes
- The overlay elements can be injected dynamically in `initializePageDropZones()` rather than hardcoded in HTML — this keeps the HTML clean and avoids invisible elements cluttering the DOM when the feature is inactive.
- `dragleave` flicker (firing when the cursor moves over a child element) is a known browser quirk. Use `relatedTarget` to check if the new target is still within the section, or use a counter approach. The `relatedTarget` approach is simpler and sufficient here.
- The `section-drop-target` class should set `position: relative` on the section so the `position: absolute` overlay is scoped correctly — confirm `#query-section` and `#tables-section` don't already have conflicting positioning.
- Only attach drag listeners when `e.dataTransfer.types` includes `'Files'` on `dragover` to avoid showing the overlay for non-file drags (e.g., text selections, links).
