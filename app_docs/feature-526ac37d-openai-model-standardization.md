# OpenAI Model Standardization to gpt-4.1

**ADW ID:** 6
**Date:** 2026-03-25
**Specification:** specs/issue-526ac37d-adw-6-sdlc_planner-update-openai-model.md

## Overview

Updated the OpenAI model used for SQL query generation and random query generation from the date-pinned `gpt-4.1-2025-04-14` to the stable alias `gpt-4.1`. The `gpt-4.1` alias always points to the most capable, up-to-date GPT-4.1 version, ensuring the application automatically benefits from model improvements without requiring manual string updates on each release.

## What Was Built

- Updated OpenAI model string in `generate_sql_with_openai` from `gpt-4.1-2025-04-14` to `gpt-4.1`
- Updated OpenAI model string in `generate_random_query_with_openai` from `gpt-4.1-2025-04-14` to `gpt-4.1`
- Updated test assertion in `test_generate_sql_with_openai_success` to match the new model name

## Technical Implementation

### Files Modified

- `app/server/core/llm_processor.py`: Updated `model` parameter in two functions — `generate_sql_with_openai` (line ~44) and `generate_random_query_with_openai` (line ~184)
- `app/server/tests/core/test_llm_processor.py`: Updated model assertion in `test_generate_sql_with_openai_success` to match `gpt-4.1`

### Key Changes

- Both OpenAI API calls now use the `gpt-4.1` alias instead of the date-pinned `gpt-4.1-2025-04-14`
- The Anthropic model (`claude-sonnet-4-0`) was not changed — only OpenAI model strings were updated
- The `gpt-4.1` alias is a stable pointer that automatically tracks the latest GPT-4.1 improvements
- Test assertions updated to reflect the new model string, maintaining test accuracy

## How to Use

No user-facing changes. The model update is transparent — SQL query generation and random query generation continue to work the same way, now using the latest GPT-4.1 capabilities automatically.

## Configuration

The model string is hardcoded in `app/server/core/llm_processor.py`. To change the model in the future, update the `model` parameter in:
- `generate_sql_with_openai` function
- `generate_random_query_with_openai` function

## Testing

```bash
cd app/server && uv run pytest
```

All existing tests should pass with the updated model name assertions.

## Notes

- The `gpt-4.1` alias removes the need for date-pinned model string updates on future OpenAI releases.
- Only two occurrences in `llm_processor.py` required updating — both are OpenAI API call sites.
- The Anthropic Claude model configuration was intentionally left unchanged per the issue scope.
