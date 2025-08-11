---
description: Bump version number, commit, tag and push
argument-hint: "[M|m|f] - M (major), m (minor), f (patch)"
---

BUMP: $ARGUMENTS

1. Bump the version number: `[string]$AppVersion` in @py-build/build-windows.ps1
    - If BUMP=M then bump major version
    - If BUMP=m then bump minor version
    - If BUMP=f or BUMP is empty then bump patch/fix version
2. Git commit
3. Git tag
4. Git push