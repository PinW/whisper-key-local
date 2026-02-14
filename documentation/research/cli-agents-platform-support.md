# CLI Coding Agents: Platform Support Analysis

*Research Date: 2026-02-14*

## Summary

Most major CLI coding agents run on Unix-like systems (macOS, Linux) with varying levels of Windows support. Windows users typically need WSL, though some tools now offer native Windows support.

---

## Platform Support by Tool

### 1. Claude Code (Anthropic)
- **Platforms:** macOS, Linux, Windows (native)
- **Windows:** Native support via Git Bash or WSL (both WSL 1 and WSL 2)
- **Notes:** v2.x series (latest v2.1.34 as of Feb 2026) runs directly in PowerShell without requiring WSL. Recent Windows-specific improvements include fixes for .bashrc handling, console flashing, OAuth tokens, proxy settings, and Japanese IME support.

### 2. OpenAI Codex CLI
- **Platforms:** macOS, Linux, Windows (WSL only)
- **Windows:** Requires WSL2 (Ubuntu)
- **Notes:** Deprecating chat/completions API in early 2026 in favor of responses API. Not natively compatible with Windows.

### 3. Gemini CLI (Google)
- **Platforms:** macOS, Linux, Windows (npm install)
- **Windows:** Technically supported via npm, but has documented platform-specific regressions after auto-updates
- **Notes:** Open-source, 1M token context window, built-in Google Search grounding. Windows stability concerns reported.

### 4. Aider
- **Platforms:** macOS, Linux, Windows (likely via WSL)
- **Windows:** Documentation suggests WSL or similar environment
- **Notes:** Python-based (3.8-3.13), installable via pip/uv. Open-source, Git-native workflows. Works best with Claude 3.7 Sonnet, DeepSeek R1, OpenAI o1/o3-mini.

### 5. Cursor CLI
- **Platforms:** macOS, Linux, Windows (native)
- **Windows:** Native support, though installation guide mentions WSL for setup
- **Notes:** Released in 2026 as companion to Cursor IDE. Model-agnostic (GPT, Gemini, Claude). Supports sudo operations, plan/ask modes, cloud agents.

### 6. Cline (VS Code Extension)
- **Platforms:** Windows, macOS, Linux (via VS Code)
- **Windows:** Native support through VS Code
- **Notes:** Not strictly a CLI tool—runs as VS Code/JetBrains extension with terminal integration. Can execute CLI commands and run in headless CI/automation workflows. Name stands for "CLI aNd Editor."

### 7. Amazon Q Developer CLI
- **Platforms:** macOS, Linux, Windows (WSL only)
- **Windows:** Not directly supported; requires WSL2
- **Notes:** Official documentation states no native Windows support as of May 2025. Open GitHub issue (#2063) requesting native Windows support with no timeline provided.

### 8. GitHub Copilot CLI
- **Platforms:** macOS, Linux, Windows (experimental native)
- **Windows:** WSL officially supported; native PowerShell is experimental and may be unstable
- **Notes:** Available via WinGet, Homebrew, npm, or install script. In public preview. Requires active Copilot subscription.

### 9. Continue
- **Platforms:** Windows, macOS, Linux (via IDE extensions)
- **Windows:** Supported through VS Code/JetBrains
- **Notes:** Open-source IDE extension with CLI/headless mode. Runs locally or remote. Supports multiple LLMs. Not a pure CLI tool but includes CLI capabilities.

### 10. Devin
- **Platforms:** Web-based (browser access)
- **Windows:** N/A (not a CLI tool)
- **Notes:** Autonomous AI agent by Cognition Labs. Not a CLI tool—accessed via web interface. Includes Devin Review for PR analysis. Updated with Sonnet 3.7 in Feb 2026.

---

## Additional Notable Tools

### Crush
- **Platforms:** macOS, Linux, Windows (PowerShell/WSL), BSD
- **Notes:** Cross-platform support including native PowerShell

### Amp (Sourcegraph)
- **Platforms:** CLI and IDE interfaces
- **Notes:** Features "Deep mode" for autonomous research and extended reasoning

---

## Windows Support Breakdown

### Native Windows Support
- **Claude Code** (v2.x+, PowerShell)
- **Cursor CLI**
- **Cline** (via VS Code)
- **Continue** (via VS Code/JetBrains)
- **Gemini CLI** (npm, but unstable)
- **Crush** (PowerShell/WSL)

### WSL Required
- **OpenAI Codex CLI** (WSL2 only)
- **Amazon Q Developer CLI** (WSL2 only)
- **Aider** (WSL recommended)

### WSL Recommended / Native Experimental
- **GitHub Copilot CLI** (WSL stable, native PowerShell experimental)

---

## Key Findings

1. **Unix Heritage:** Most CLI coding agents originate from Unix/Linux environments and have strongest support there.

2. **WSL as Workaround:** Tools without native Windows support typically work through WSL2, which provides a Linux environment on Windows.

3. **Native Windows Progress:** Claude Code and Cursor CLI lead in native Windows support (2026), with recent stability improvements specifically for Windows environments.

4. **VS Code Bridge:** IDE extensions like Cline and Continue offer Windows support through VS Code's cross-platform architecture while providing CLI-like capabilities.

5. **Installation Methods:** Most tools install via npm, pip/uv, Homebrew (macOS/Linux), or WinGet (Windows).

---

## Sources

- [Claude Code Setup Documentation](https://code.claude.com/docs/en/setup)
- [Claude Code Windows Installation Guide](https://interworks.com/blog/2026/01/27/how-to-install-claude-code-on-windows-11/)
- [Aider Installation Documentation](https://aider.chat/docs/install.html)
- [GitHub Copilot CLI Documentation](https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli)
- [GitHub Copilot CLI Repository](https://github.com/github/copilot-cli)
- [Amazon Q Developer CLI for Windows](https://builder.aws.com/content/2v5PptEEYT2y0lRmZbFQtECA66M/the-essential-guide-to-installing-amazon-q-developer-cli-on-windows)
- [Amazon Q CLI WSL2 Installation](https://repost.aws/articles/ARRW-I9s_cSP2NS2WZhYilQQ/how-to-install-amazon-q-developer-cli-on-wsl2)
- [Cursor CLI Updates January 2026](https://www.theagencyjournal.com/cursors-cli-just-got-a-whole-lot-smarter-fresh-updates-from-last-week/)
- [Cursor CLI Complete Guide](https://www.codecademy.com/article/getting-started-with-cursor-cli)
- [Cline VS Code Extension](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev)
- [Cline GitHub Repository](https://github.com/cline/cline)
- [Gemini CLI Documentation](https://developers.google.com/gemini-code-assist/docs/gemini-cli)
- [Gemini CLI GitHub Repository](https://github.com/google-gemini/gemini-cli)
- [OpenAI Codex CLI Repository](https://github.com/openai/codex)
- [OpenAI Codex Changelog](https://developers.openai.com/codex/changelog/)
- [Continue GitHub Repository](https://github.com/continuedev/continue)
- [Continue Documentation](https://docs.continue.dev/)
- [Devin 2.0 Announcement](https://cognition.ai/blog/devin-2)
- [2026 Guide to Coding CLI Tools](https://www.tembo.io/blog/coding-cli-tools-comparison)
- [Top 5 CLI Coding Agents in 2026](https://pinggy.io/blog/top_cli_based_ai_coding_agents/)
- [Claude Code Windows Native Installation](https://smartscope.blog/en/generative-ai/claude/claude-code-windows-native-installation/)
- [CLI Tools Comparison: Claude vs Codex vs Gemini](https://www.codeant.ai/blogs/claude-code-cli-vs-codex-cli-vs-gemini-cli-best-ai-cli-tool-for-developers-in-2025)
