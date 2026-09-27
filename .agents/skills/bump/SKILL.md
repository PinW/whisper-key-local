---
name: bump
description: "Bump version number, commit, tag and push"
argument-hint: "[M|m|f] - M (major), m (minor), f (patch)"
---

BUMP: $ARGUMENTS

1. Read [CURRENT VERSION] from @pyproject.toml
2. Calculate [NEW VERSION] `M.m.f`:
    - If BUMP=M then bump major version
    - If BUMP=m then bump minor version
    - If BUMP=f or BUMP is empty then bump patch/fix version
    - v0.x.x: minor = patch
3. Ask user to confirm: "Bump version from [CURRENT VERSION] to [NEW VERSION]?"
4. Update version in pyproject.toml
5. Git commit
6. Git tag
7. Git push
