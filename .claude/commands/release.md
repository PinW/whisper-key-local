---
description: Release the latest git tagged version
allowed-tools: Bash(git *), Bash(gh *)
---

1. Get the two latest git tags: !`git tag --sort=-v:refname | head -2`
2. Use `git log [PREVIOUS_TAG]..[LATEST_TAG] --format="%s%n%b---"`
3. Update @CHANGELOG.md with [LATEST_TAG] based on those commits
4. Commit changelog and re-tag: `git add CHANGELOG.md && git commit -m "Update CHANGELOG.md for [VERSION] release" && git tag -d [VERSION] && git tag [VERSION]`
5. Git push
6. Create GitHub release: `gh release create [VERSION] --draft=false --title "[VERSION]" --notes "[VERSION CHANGELOG]"` (omit the `## [VERSION] - DATE` header)
7. Build for PyPI: `powershell.exe -Command "cd [WSL_PROJECT_PATH]; python -m build"`
8. Upload to PyPI: `powershell.exe -Command "twine upload [WSL_PROJECT_PATH]\\dist\\*"`
9. Build pyapp exe: `/build-pyapp-exe` (depends on PyPI package being available)
10. Upload exe to release: `gh release upload [VERSION] [PATH_TO_EXE]`