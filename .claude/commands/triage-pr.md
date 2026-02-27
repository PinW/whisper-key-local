---
description: Triage GitHub PR review comments one by one
---

Triage review comments from a GitHub PR. Argument: PR number or URL (e.g. `/triage-pr 42`).

## Steps

1. Fetch the PR review comments using `gh pr view <number> --comments` and `gh api repos/{owner}/{repo}/pulls/{number}/comments`
2. Parse out individual review suggestions/comments (skip resolved ones)
3. For each comment, present it to the user one at a time with:
   - The file and line(s) referenced
      - The reviewer's comment text
      - Any suggested code change
   - For each comment, analyze:
      - **Is it real?** — Is the reviewer's observation factually correct? (Check the code to verify)
      - **Do we care?** — Even if correct, is it worth acting on?
5. Ask user whether to:
   - Make the fix
   - Move to the next comment
6. After all comments are triaged, summarize what was changed and what was skipped