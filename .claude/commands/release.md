---
description: Release the latest git tagged version
allowed-tools: Bash(git describe:*), Bash(git tag:*), Bash(gh release:*), Bash(gh:*)
---

1. Get the two latest git tags: !`git tag --sort=-v:refname | head -2`
2. Use `git log [PREVIOUS_TAG]..[LATEST_TAG] --oneline`
3. Update @CHANGELOG.md with [LATEST_TAG] based on those commits (make sure to give credit contributors with merged PRs)
4. Commit changelog and re-tag: `git add CHANGELOG.md && git commit -m "Update CHANGELOG.md for [VERSION] release" && git tag -d [VERSION] && git tag [VERSION]`
5. Git push
6. Create GitHub release: `gh release create [VERSION] --title "[VERSION]"" --notes "[VERSION CHANGELOG]"`
7. Re-build for PyInstaller: `powershell.exe -ExecutionPolicy Bypass -File /home/pin/whisper-key-local/py-build/build-windows.ps1`
8. Upload built zip to release: `gh release upload [VERSION] [PATH_TO_ZIP]`
9. Re-build and upload to PyPI: `powershell.exe -Command "python -m build && twine upload dist/*"`