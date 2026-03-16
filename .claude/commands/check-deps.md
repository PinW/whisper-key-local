---
description: Check upstream dependencies for updates
allowed-tools: Read, Bash(pip:*), WebFetch, WebSearch, Agent
---

Check all dependencies in @pyproject.toml for upstream updates.

For each dependency:
1. Read the pinned/minimum version from pyproject.toml
2. Check latest version on PyPI: `~/.venv/bin/pip index versions <package> 2>/dev/null | head -1`
3. If newer version exists, fetch the changelog/release notes (check PyPI page or GitHub releases)

## Special attention: ctranslate2

ctranslate2 is PINNED (==) because:
- AMD ROCm wheels in `onboarding.py` must match the exact version
- ROCm wheel URLs in `PinW/ctranslate2-rocm-wheels` need updating if version changes
- NVIDIA CUDA runtime package compatibility may change between versions

If a new ctranslate2 version exists:
- Check GitHub releases at https://github.com/OpenNMT/CTranslate2/releases for changelog
- Check if new version has `rocm-python-wheels-Windows.zip` release asset
- Check if faster-whisper has been updated to support the new version
- Flag any breaking changes or API changes

## Output format

For each dependency with an update available:

```
<package>: <current> → <latest>
  Breaking changes: <yes/no + details>
  New features: <brief summary>
  Recommendation: <update/hold/investigate>
  Notes: <any relevant context>
```

End with a summary table of all dependencies and their status.
