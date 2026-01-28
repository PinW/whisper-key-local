---
name: worktree-setup
description: Create a git worktree and set up symlinks to shared gitignored files
disable-model-invocation: false
allowed-tools: Bash(python3 *), Bash(git worktree *)
---

Create a worktree and set up symlinks:

```bash
python3 .claude/skills/worktree-setup/scripts/setup-worktree.py <project-name> <branch-name>
```
