# pr-scout

AI-powered PR checks as GitHub Actions. See `SPEC.md` for full details.

## Current State

`audit_spec.py` is a reference copy from `exp-1-audit-spec-change` — it uses
Ollama's API and needs to be rewritten against an OpenAI-compatible API.

## Model

Default model: `vertex_ai.gemini-2.5-flash` — cheap, fast, sufficient for
diff summarization and spec comparison tasks.
