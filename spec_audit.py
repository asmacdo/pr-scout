#!/usr/bin/env python3
"""Audit whether a PR's spec changes match its code changes."""

import json
import os
import subprocess
import sys
import urllib.request
from dataclasses import asdict, dataclass

SPEC_CANDIDATES = ["SPEC.md", "SPEC.rst", "SPEC", "spec.md", "docs/SPEC.md"]


def _require_env(name):
    """Return the value of a required environment variable or exit."""
    value = os.environ.get(name)
    if not value:
        print(f"error: {name} is not set", file=sys.stderr)
        sys.exit(1)
    return value.strip()


@dataclass
class Result:
    status: str  # no_spec, no_code_changes, missing_spec_update, pass, fail
    spec_file: str = ""
    summary: str = ""
    verdict: str = ""


def git(*args, repo=None):
    """Run a git command and return (stdout, returncode)."""
    cmd = ["git"]
    if repo:
        cmd += ["-C", repo]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.returncode


def find_spec(repo, ref):
    """Find the spec file in the repo at the given ref."""
    for candidate in SPEC_CANDIDATES:
        _, rc = git("show", f"{ref}:{candidate}", repo=repo)
        if rc == 0:
            return candidate
    return None


def get_diff(repo, base, pr, *pathspec):
    """Get diff between base and pr, optionally filtered by pathspec."""
    args = ["diff", f"{base}...{pr}", "--"]
    args += list(pathspec)
    stdout, rc = git(*args, repo=repo)
    if rc != 0:
        raise RuntimeError(f"git diff failed for {base}...{pr}")
    return stdout


def ask_llm(prompt, api_base, api_token, model):
    """Send a prompt to an OpenAI-compatible API and return the response text."""
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        f"{api_base}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}",
        },
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
    return body["choices"][0]["message"]["content"]


def _summarize(code_diff, api_base, api_token, model):
    """Ask the LLM to summarize what a code diff does."""
    return ask_llm(
        "Summarize the new or changed functionality in this diff. "
        "Be specific about what behavior changed. "
        "List each change as a bullet point. "
        "Do NOT describe documentation or spec changes.\n\n"
        f"```diff\n{code_diff}\n```",
        api_base, api_token, model,
    )


def _compare(summary, spec_diff, api_base, api_token, model):
    """Ask the LLM whether a spec update matches a code change summary."""
    return ask_llm(
        "A pull request changes both code and a spec document.\n\n"
        "Here is a summary of what the CODE changes do:\n"
        f"{summary}\n\n"
        "Here is the SPEC diff:\n"
        f"```diff\n{spec_diff}\n```\n\n"
        "Does the spec update accurately describe the code changes?\n"
        "Focus on user-visible behavior only — ignore internal implementation "
        "details like variable names, method calls, or code structure.\n"
        "- List any user-visible functionality NOT covered by the spec update.\n"
        "- List any spec claims that contradict the actual behavior.\n"
        "- If they match well, say PASS.\n"
        "- If there are problems, say FAIL and explain.",
        api_base, api_token, model,
    )


def audit(repo, base, pr):
    """Run the full spec audit and return a Result."""
    api_base = _require_env("PR_SCOUT_OPENAI_BASE_URL")
    api_token = _require_env("PR_SCOUT_OPENAI_API_KEY")
    model = _require_env("PR_SCOUT_MODEL")

    spec_file = find_spec(repo, pr)
    if not spec_file:
        return Result(status="no_spec")

    code_diff = get_diff(repo, base, pr, ".", f":!{spec_file}")
    spec_diff = get_diff(repo, base, pr, spec_file)

    if not code_diff.strip():
        return Result(status="no_code_changes", spec_file=spec_file)

    summary = _summarize(code_diff, api_base, api_token, model)

    if not spec_diff.strip():
        return Result(
            status="missing_spec_update", spec_file=spec_file, summary=summary,
        )

    verdict = _compare(summary, spec_diff, api_base, api_token, model)
    passed = "FAIL" not in verdict.upper().split("\n")[0]

    return Result(
        status="pass" if passed else "fail",
        spec_file=spec_file,
        summary=summary,
        verdict=verdict,
    )


def format_comment(result):
    """Build a markdown PR comment from a Result."""
    status_line = {
        "no_code_changes": "PR only changes the spec",
        "missing_spec_update": "⚠️ Code changed but spec was not updated",
        "pass": "✅ Spec update matches code changes",
        "fail": "❌ Spec update does not match code changes",
    }
    lines = [
        "## pr-scout: spec-audit",
        "",
        "<details>",
        f"<summary>{status_line[result.status]}</summary>",
    ]

    if result.summary:
        lines += ["", "### Code change summary", "", result.summary]

    if result.verdict:
        lines += ["", "### Verdict", "", result.verdict]

    lines += ["", "</details>"]
    return "\n".join(lines)


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <repo-path> <base-ref> <pr-ref>",
              file=sys.stderr)
        sys.exit(1)

    repo, base, pr = sys.argv[1], sys.argv[2], sys.argv[3]
    result = audit(repo, base, pr)

    if result.status == "no_spec":
        candidates = ", ".join(SPEC_CANDIDATES)
        print(f"No spec file found (looked for: {candidates}), nothing to audit.",
              file=sys.stderr)
        sys.exit(1)

    output = asdict(result)
    output["comment"] = format_comment(result)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
