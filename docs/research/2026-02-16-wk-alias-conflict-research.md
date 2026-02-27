# Research: Is `wk` Safe to Use as a CLI Alias?

**Date:** 2026-02-16
**Verdict:** Safe to use. No meaningful conflicts.

---

## 1. Built-in OS Commands

| Platform | Built-in? | Notes |
|----------|-----------|-------|
| Linux/WSL (Ubuntu, Debian, etc.) | No | Not a standard command. No package named `wk` in apt. |
| macOS | No | Not a built-in command or system utility. |
| Windows CMD | No | Not a built-in command. |
| PowerShell | No | Not a default alias. PowerShell built-in aliases do not include `wk`. |

`wk` does not conflict with any built-in command on any major OS.

## 2. Package Manager Registry Check

| Registry | Package named `wk`? | Installs `wk` binary? | Popularity |
|----------|---------------------|----------------------|------------|
| **apt** (Ubuntu/Debian) | No | No | N/A |
| **Homebrew** (macOS/Linux) | No formula named `wk` | No | N/A |
| **npm** | Yes (`wk`) - spreadsheet previewer | Likely (via npx) | Very low; published 3+ years ago |
| **pip** (PyPI) | No package named `wk` | No | N/A |
| **cargo** (crates.io) | No crate named `wk` | No | N/A |

No major package manager installs a widely-used `wk` binary.

## 3. Third-Party CLI Tools Named `wk`

Several obscure, low-adoption projects use the name `wk`:

| Tool | Purpose | Language | Popularity | Source |
|------|---------|----------|------------|--------|
| [gpanders/wk](https://sr.ht/~gpanders/wk/) | Personal wiki manager | Nim | Very low; last activity 3+ years ago | SourceHut |
| [henrybarreto/wk](https://github.com/henrybarreto/wk) | Directory navigation / workspaces | Rust | 1 star, 0 forks | GitHub |
| [mconbere/wk](https://github.com/mconbere/wk) | Workspace auto-setup | Unknown | Negligible | GitHub |
| [alperr/wk](https://github.com/alperr/wk) | Web app builder CLI | JS | Negligible | GitHub |
| [wk.js.org](https://wk.js.org/) | SPA builder using web components | JS (binary download) | Negligible | Website |

None of these tools are widely known or commonly installed. None appear in default package manager repositories.

## 4. Common Alias Conventions

- `wk` is not a widely-used conventional alias for anything (unlike `ll`, `gs`, `k`, etc.)
- The `WK` prefix is used internally by the WebKit project for variables (e.g., `WK_USE_CCACHE`), but this is source-code level, not a CLI command
- Apache OpenWhisk uses `wsk` (not `wk`) as its CLI command
- `wkhtmltopdf` exists but its binary is `wkhtmltopdf`, not `wk`

## 5. Summary

**`wk` is safe to use as a CLI alias for whisper-key.** The name has:

- Zero conflicts with built-in OS commands on any platform
- Zero conflicts with any popular CLI tool
- Zero conflicts with default package manager packages (apt, brew, pip, cargo)
- Only trivial conflicts with a handful of abandoned/obscure projects that users would essentially never encounter
- The npm package `wk` exists but is for a completely different purpose (spreadsheet preview) and would not typically be installed globally

The only `wk` currently on this system is a custom script at `~/bin/wk` that already calls `run-whisper-key` via PowerShell, confirming the alias is already in use for this project.
