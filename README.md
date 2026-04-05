# pr-scout

AI-powered checks for pull requests, packaged as a GitHub Action.

## Quick start

```yaml
on: pull_request
permissions:
  pull-requests: write
jobs:
  spec-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: asmacdo/pr-scout@main
        with:
          check: spec-audit
        env:
          PR_SCOUT_OPENAI_BASE_URL: ${{ secrets.PR_SCOUT_OPENAI_BASE_URL }}
          PR_SCOUT_OPENAI_API_KEY: ${{ secrets.PR_SCOUT_OPENAI_API_KEY }}
          PR_SCOUT_MODEL: ${{ secrets.PR_SCOUT_MODEL }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Checks

### spec-audit

Detects whether a PR that changes code also updates the project's spec,
and whether that update accurately reflects the code changes.

| Status | Meaning | Job result |
|---|---|---|
| `no_spec` | No spec file found | skipped (no comment) |
| `no_code_changes` | PR only touches the spec | pass |
| `missing_spec_update` | Code changed, spec not updated | fail |
| `pass` | Spec update matches the code | pass |
| `fail` | Spec update contradicts the code | fail |

## Demo

See [asmacdo/pr-scout-dummy](https://github.com/asmacdo/pr-scout-dummy) for
a live example:

- [PR #2](https://github.com/asmacdo/pr-scout-dummy/pull/2) -- no spec file, check skipped
- [PR #3](https://github.com/asmacdo/pr-scout-dummy/pull/3) -- spec matches code changes, passes
- [PR #4](https://github.com/asmacdo/pr-scout-dummy/pull/4) -- spec contradicts code, fails with explanation

## Configuration

| Variable | Description |
|---|---|
| `PR_SCOUT_OPENAI_BASE_URL` | OpenAI-compatible API base URL (including `/v1`) |
| `PR_SCOUT_OPENAI_API_KEY` | API key for the LLM endpoint |
| `PR_SCOUT_MODEL` | Model identifier (e.g. `vertex_ai.gemini-2.5-flash`) |

## CLI usage

```bash
export PR_SCOUT_OPENAI_BASE_URL=https://api.example.com/v1
export PR_SCOUT_OPENAI_API_KEY=sk-...
export PR_SCOUT_MODEL=vertex_ai.gemini-2.5-flash
python spec_audit.py <repo-path> <base-ref> <pr-ref>
```

Outputs JSON to stdout. See [SPEC.md](SPEC.md) for full details.
