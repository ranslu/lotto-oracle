# CLAUDE.md

## Priority #1: save tokens
- Do the least work that finishes the task. Don't re-read files already read, re-derive settled facts, or explore beyond what the task needs.
- Prefer targeted reads (`grep`, `sed -n`, line ranges) over whole-file dumps; `lottery_data.json` is large — never cat it whole.
- Batch independent tool calls in one turn. No subagents unless asked.
- Keep replies short: result first, no narration of options not taken.
- Keep this file short — it is loaded into every session.

## Project
Streamlit lottery-picks app. Entry: `lotto2.py`. Data fetch: `fetch_lottery.py` → `lottery_data.json`. Email: `email_picks.py`. Deps: `requirements.txt`.

## Reference
- LLM token/prompt-caching cost notes: `.claude/skills/token-caching/SKILL.md` (loaded on demand via the `token-caching` skill).
