# Chore: Update OpenAI Model to Latest Version

## Metadata
issue_number: `526ac37d`
adw_id: `6`
issue_json: `{"number":6,"title":"Support better models for query generation","body":"chore - adw_sdlc_iso\n\nupdate openai model to use latest openai model"}`

## Chore Description
Update the OpenAI model used for SQL query generation and random query generation from the current `gpt-4.1-2025-04-14` to the latest available OpenAI model (`gpt-4.1`). The `gpt-4.1` alias always points to the most capable, up-to-date version of GPT-4.1, ensuring the application benefits from the best available model without needing to update the date-pinned model string on each release.

## Relevant Files

- `app/server/core/llm_processor.py` — Contains the OpenAI model string in two functions: `generate_sql_with_openai` (line 44) and `generate_random_query_with_openai` (line 184). Both currently use `gpt-4.1-2025-04-14` and need to be updated to `gpt-4.1`.
- `app/server/tests/core/test_llm_processor.py` — Contains test assertions that verify the exact model string passed to the OpenAI API (line 44: `assert call_args[1]['model'] == 'gpt-4.1-2025-04-14'`). Must be updated to match the new model name.

## Step by Step Tasks

### Step 1: Update OpenAI model in `llm_processor.py`
- In `app/server/core/llm_processor.py`, update the `model` parameter in `generate_sql_with_openai` from `"gpt-4.1-2025-04-14"` to `"gpt-4.1"`
- In `app/server/core/llm_processor.py`, update the `model` parameter in `generate_random_query_with_openai` from `"gpt-4.1-2025-04-14"` to `"gpt-4.1"`

### Step 2: Update test assertions in `test_llm_processor.py`
- In `app/server/tests/core/test_llm_processor.py`, update the assertion `assert call_args[1]['model'] == 'gpt-4.1-2025-04-14'` to `assert call_args[1]['model'] == 'gpt-4.1'` in `test_generate_sql_with_openai_success`

### Step 3: Run validation commands
- Run the server tests to confirm all tests pass with zero regressions

## Validation Commands
Execute every command to validate the chore is complete with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the chore is complete with zero regressions

## Notes
- Only the OpenAI model needs updating per the issue. The Anthropic model (`claude-sonnet-4-0`) is not mentioned and should remain unchanged.
- The `gpt-4.1` alias is the stable pointer to the latest GPT-4.1 model, removing the need for future date-pinned updates.
- Two occurrences in `llm_processor.py` must be updated: one in `generate_sql_with_openai` and one in `generate_random_query_with_openai`.
- One test assertion in `test_llm_processor.py` must be updated to match the new model name.
