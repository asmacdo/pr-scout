# pr-scout

AI-powered checks for pull requests, packaged as GitHub Actions.

## Overview

pr-scout runs lightweight LLM-based checks on PRs and posts results as
comments. The first check is **spec-audit**: does the PR's spec update match
its code changes?

## Architecture

- Each check is a standalone Python script (no framework dependencies beyond
  stdlib) that reads a repo and writes JSON to stdout.
- A composite GitHub Action dispatches to the requested check, captures its
  output, and posts a PR comment.
- The `check` input selects which script to run. Each check owns its own
  configuration, prompts, and output schema.
- Any OpenAI-compatible API can be used as the LLM backend.

## Checks

### spec-audit

Detects whether a PR that changes code also updates the project's spec, and
whether that update accurately reflects the code changes.

**Inputs:** a checked-out repo with base and PR refs available.

**Steps:**

1. Find the spec file (`SPEC.md` and common variants) in the repo.
2. Split the PR diff into code changes and spec changes.
3. Ask the LLM to summarize the code changes (without seeing the spec).
4. Ask the LLM to compare the summary against the spec diff.
5. Report the result.

**Statuses:**

- `no_spec` — repo has no spec file. No action taken.
- `no_code_changes` — PR only touches the spec. No audit needed.
- `missing_spec_update` — code changed but spec was not updated.
- `pass` — spec update matches the code changes.
- `fail` — spec update does not match or contradicts the code changes.

**Exit codes:** 0 when the audit completes (any status). Non-zero when the
tool itself fails (missing config, git error, LLM unreachable).

## Configuration

Environment variables (all prefixed `PR_SCOUT_`):

| Variable | Required | Description |
|---|---|---|
| `PR_SCOUT_OPENAI_BASE_URL` | yes | OpenAI-compatible API base URL |
| `PR_SCOUT_OPENAI_API_KEY` | yes | API key for the LLM endpoint |
| `PR_SCOUT_MODEL` | yes | Model identifier |

## Usage

### As a GitHub Action (target repo)

Add a workflow that references the action and provide secrets:

```yaml
on: pull_request
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

### CLI

```bash
export PR_SCOUT_OPENAI_BASE_URL=https://api.example.com/v1
export PR_SCOUT_OPENAI_API_KEY=sk-...
export PR_SCOUT_MODEL=vertex_ai.gemini-2.5-flash
python spec_audit.py <repo-path> <base-ref> <pr-ref>
```

## Output

`spec_audit.py` writes JSON to stdout:

```json
{"status": "pass", "spec_file": "SPEC.md", "summary": "...", "verdict": "..."}
```

The composite action captures this output and posts a PR comment.
The script itself has no GitHub dependency.
