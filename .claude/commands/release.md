---
description: Release the latest git tagged version
allowed-tools: Bash(git describe:*), Bash(git tag:*), Bash(gh release:*), Bash(gh:*)
---

1. Get latest git tag version: !`git describe --tags --abbrev=0`
2. Update @CHANGELOG.md based on tagged version
3. Commit changelog and re-tag: `git add CHANGELOG.md && git commit -m "Update CHANGELOG.md for [VERSION] release" && git tag -d [VERSION] && git tag [VERSION]`
4. Create GitHub release: `gh release create [VERSION] --title "[VERSION]"" --notes "[YOUR NOTES HERE]"`
5. Re-build the app
6. Upload built zip to release: `gh release upload [VERSION] [PATH_TO_ZIP]`