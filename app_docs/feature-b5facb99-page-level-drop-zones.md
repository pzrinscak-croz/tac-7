# Page-Level Drag-and-Drop Zones

**ADW ID:** b5facb99
**Date:** 2026-03-25
**Specification:** specs/issue-1-adw-b5facb99-sdlc_planner-increase-drop-zone-area.md

## Overview

This feature extends the drag-and-drop file upload surface area beyond the upload modal. Users can now drag files directly onto the `#query-section` (upper div) or `#tables-section` (lower div) of the main page, seeing a "Drop to create table" overlay as visual feedback. On drop, the existing `handleFileUpload` function processes the file — no modal interaction required.

## What Was Built

- Page-level drag-and-drop listeners on `#query-section` and `#tables-section`
- Dynamically injected overlay elements with "Drop to create table" text
- CSS classes for section highlight (`section-dragover`) and overlay visibility (`section-drop-overlay`, `.visible`)
- `dragleave` flicker prevention using `relatedTarget` check
- File-only drag guard: overlay only appears when `dataTransfer.types` includes `'Files'`

## Technical Implementation

### Files Modified

- `app/client/src/main.ts`: Added `initializePageDropZones()` function; called from `DOMContentLoaded` handler
- `app/client/src/style.css`: Added `.section-drop-target`, `.section-dragover`, `.section-drop-overlay`, and `.section-drop-overlay.visible` CSS classes

### Key Changes

- `initializePageDropZones()` iterates over `['query-section', 'tables-section']`, adds the `section-drop-target` class (sets `position: relative`), and dynamically appends a `div.section-drop-overlay` to each section
- `dragover` handler checks `e.dataTransfer?.types.includes('Files')` before activating — prevents overlay on text/link drags
- `dragleave` handler uses `section.contains(e.relatedTarget)` to avoid premature overlay removal when the cursor moves over child elements
- `drop` handler extracts `e.dataTransfer.files[0]` and delegates to the existing `handleFileUpload(file)` — no new upload logic
- Overlay is styled with a semi-transparent `rgba(102, 126, 234, 0.12)` background, centered pill text using `var(--primary-color)`, and `pointer-events: none` so it doesn't interfere with child interactions

## How to Use

1. Open the application in the browser
2. Drag a `.csv`, `.json`, or `.jsonl` file from your filesystem over the upper (query input) or lower (available tables) section
3. The section highlights with a dashed border and a "Drop to create table" overlay appears
4. Release the file — the table is created and a success message appears, identical to the modal upload flow
5. Moving away without dropping hides the overlay and restores normal appearance

## Configuration

No configuration required. The feature initializes automatically on `DOMContentLoaded` alongside other existing initializers.

## Testing

- Drag a supported file (`.csv`, `.json`, `.jsonl`) over `#query-section` — verify overlay appears and table is created on drop
- Drag the same file over `#tables-section` — verify identical behavior
- Drag a non-file item (e.g., selected text) — verify overlay does not appear
- Move cursor away without dropping — verify overlay hides cleanly
- Verify the existing modal drop zone still works independently

## Notes

- Only `files[0]` is processed on drop, matching existing modal behavior — multi-file drops silently ignore subsequent files
- The modal remains fully functional and unchanged; the new zones are additive
- Overlay elements are injected dynamically in JS to keep `index.html` clean
