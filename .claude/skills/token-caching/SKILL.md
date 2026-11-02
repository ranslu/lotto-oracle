---
name: token-caching
description: Cost-saving reference for LLM prompt/token caching (Anthropic, OpenAI, Gemini) and caching tools (LiteLLM, LangChain/LlamaIndex, vLLM/SGLang, OpenRouter, Open-WebUI). Use whenever adding or changing any LLM API call in this project, or when asked how to cut AI/API costs.
---

# Token caching — saving money on LLM calls

Caching cuts **input** token cost 50–90% when the prompt *prefix* is identical across requests within the cache window.

## Provider pricing (cached input)
| Provider | Cache read | Notes |
|---|---|---|
| Anthropic (Claude) | 0.1× base input (90% off) | Opt-in via `cache_control` breakpoints. Cache **writes** cost 1.25× (5-min TTL) or 2× (1-hour TTL). Minimum cacheable prefix ~1–4K tokens depending on model. |
| OpenAI | ~50%+ off (higher on newer models) | Automatic for prompts ≥1024 tokens with matching prefix. |
| Google Gemini | up to ~75% off | Implicit caching + explicit cached-content API (storage billed per hour). |

Verify current numbers before quoting them (the `claude-api` skill has live Anthropic pricing).

## Where savings are biggest
- Long, fixed system prompts / rule sets / brand guides.
- RAG: many follow-ups over the same document.
- Agent loops: 10–20 tool calls reusing the same history.

## Rules for cache hits
- Put stable content first (tools → system → documents), variable content (user question, timestamps) last.
- Never put timestamps, random IDs, or reordered lists in the prefix — one changed byte invalidates everything after it.
- Calls must recur inside the TTL (Anthropic 5 min default / 1 h option; OpenAI ~5–10 min, up to 1 h off-peak).
- Check `usage.cache_read_input_tokens` (Anthropic) / `cached_tokens` (OpenAI) to confirm hits.

## Tools
1. **LiteLLM proxy** — one gateway for OpenAI/Anthropic/Gemini; can auto-inject `cache_control`; optional Redis response cache (identical prompt → $0).
2. **LangChain `set_llm_cache()` / LlamaIndex caches** — in-memory, SQLite or Redis response caching; semantic caching via vector DB (Qdrant/Redis) for paraphrased repeats.
3. **vLLM / SGLang** (self-hosted) — automatic prefix/KV caching (PagedAttention, RadixAttention); 2–4× more concurrent requests per GPU.
4. **OpenRouter** — sticky provider routing keeps provider-side caches warm.
5. **Open-WebUI Pipelines** — custom pipeline can inject cache breakpoints into system messages.

## Decision guide
- Calling a hosted API directly → structure prompts for prefix caching (+ `cache_control` on Anthropic).
- Many identical questions → add a response cache (Redis/LiteLLM/LangChain).
- Self-hosting models → vLLM or SGLang with prefix caching on.
