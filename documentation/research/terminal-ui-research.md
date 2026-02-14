# Terminal UI Research for Dev Tools

*2026-02-13*

How Sidecar, Claude Code, lazygit, and other terminal-based dev tools build their terminal UIs -- frameworks, rendering strategies, input handling, and what's relevant for a Python app like Whisper Key.

---

## How Real Tools Do It

### Claude Code (TypeScript + Ink/React)

Claude Code uses **React + Ink** (React for CLIs) with a **custom renderer rewrite**. Ink's default rendering clears and redraws the entire terminal every state change (~30 FPS cap), causing catastrophic flickering that crashed VSCode's terminal and generated 4,000-6,700 scroll events/second in tmux. Anthropic rewrote the renderer with:

- Double-buffering with cell-level diffing (only changed cells emit ANSI)
- Packed TypedArrays for screen buffers (reduces GC pressure)
- ~16ms frame budget targeting ~5ms for the render pipeline
- DEC mode 2026 (synchronized output) pushed upstream to VSCode and tmux

Critical design decision: renders into **normal scrollback** (not alternate screen buffer like vim), preserving native text selection and terminal search. Layout: status bar (top), scrollable conversation (middle), fixed input area (bottom) via Yoga flexbox.

### Sidecar (Go + Bubble Tea)

Sidecar uses the full **Charmbracelet ecosystem**: Bubble Tea (Elm Architecture MVU framework), Lipgloss (CSS-like styling), Bubbles (components), Glamour (markdown rendering). Also supports Sixel graphics for in-terminal images.

Layout composed via `JoinVertical()`/`JoinHorizontal()` string concatenation. Panels include file tracking, syntax-highlighted diffs, code preview, conversation browser, task monitoring, and token usage.

### Crush/OpenCode (Go + Bubble Tea v2)

Charmbracelet's own AI coding TUI. Architecture: "smart main model, dumb components" -- only the central `UI.Update()` processes messages; components expose imperative methods (`SetSize()`, `Focus()`, `Blur()`) returning `tea.Cmd`. Responsive breakpoints: compact mode when width < 120 or height < 30. PubSub event system for background operations.

### OpenAI Codex CLI (Rust + Ratatui)

OpenAI migrated from TypeScript/Ink to **Rust + Ratatui + Crossterm** to eliminate Node.js runtime dependency. Immediate-mode rendering with constraint-based layout (`Constraint::Percentage`, `Min`, `Length`). Double-buffered: only changed cells sent to terminal.

### lazygit (Go + custom gocui fork)

Uses a **custom fork of gocui**, not Bubble Tea. Views are rectangular text buffers; multiple views can share a "window" with tabs. Four-layer architecture: UI -> GUI management (controllers/helpers) -> Git commands -> infrastructure. Navigation uses a **context stack** pattern (like mobile nav). Keybindings operate at context-specific, global, and user-custom levels.

### Aider (Python + Rich + prompt_toolkit)

Conversational REPL, **not a full-screen TUI**. Rich formats output (markdown, syntax highlighting, diffs). prompt_toolkit provides readline-like input with autocomplete and history. Deliberately stays simple -- linear scrolling output, no panels or splits.

### Gemini CLI (TypeScript + React + Ink)

Same stack as Claude Code: React + Ink with Yoga flexbox. Upgraded to Ink 6 + React 19.

### Warp Terminal (Rust + custom GPU renderer)

Not a TUI -- a native GPU-rendered application. Custom Rust + Metal/wgpu framework achieving 144+ FPS at 4K. Average screen redraw: 1.9ms. In its own category entirely.

---

## Framework Landscape

### By Language

| Framework | Language | Type | Architecture | Best For |
|-----------|----------|------|-------------|----------|
| **Textual** | Python | App framework | Retained/reactive, CSS-like | Full-screen TUI apps |
| **Rich** | Python | Output library | Immediate | Inline progress, tables, logging |
| **prompt_toolkit** | Python | Input framework | Event-driven | REPLs, command input |
| **Bubble Tea** | Go | App framework | Elm MVU | Interactive TUI apps |
| **Ratatui** | Rust | Rendering library | Immediate mode | Performance-critical TUIs |
| **Ink** | TypeScript | App framework | React reconciler + Yoga | Inline interactive CLIs |

### The Elm Architecture (MVU) Dominates

The Model-View-Update pattern is the common thread:
- **Bubble Tea**: enforces it directly
- **Ratatui**: apps commonly adopt it (though unopinionated)
- **React/Ink**: unidirectional data flow is conceptually similar
- **Textual**: reactive attributes + event-driven messaging

```
Event -> Update(model, msg) -> (new model, cmd) -> View(model) -> terminal output
```

---

## Key Rendering Concepts

### Alternate Screen vs Inline

| Approach | Used By | Pros | Cons |
|----------|---------|------|------|
| **Alternate buffer** (`ESC[?1049h`) | vim, lazygit, k9s | Clean canvas, perfect restore on exit | Loses scrollback history |
| **Inline/scrollback** | Claude Code, cargo, Aider | Preserves context, native text selection | Harder to implement, cursor management |

### Flicker Prevention

1. **Double buffering**: render to back buffer, diff against front, emit only changes
2. **Synchronized output** (DEC mode 2026): terminal batches all writes between begin/end markers
3. **Overwrite don't clear**: write new content over old instead of clear-then-write

### Rendering Modes

- **Immediate mode** (Ratatui, Bubble Tea): redraw entire UI each frame as pure function of state. Simpler mental model, must diff output.
- **Retained mode** (Textual, curses): persistent widget tree with targeted re-renders. More complex, more efficient for large UIs.

---

## Python Options for Whisper Key

### Option 1: Rich Only (Minimal Migration)

Swap `StreamHandler` for `RichHandler` for instant pretty logging. Add `Rich.Live` for dynamic status displays. Works alongside existing `print()`/`logging`.

- `Live` context manager for updating content (configurable refresh rate)
- `Layout` divides terminal into named regions (header/body/footer)
- Thread-safe: `Console` is safe for printing, `Live` uses internal refresh thread
- Can `print()` above a live display without disruption

**Effort**: Minimal. Incremental adoption, no restructuring needed.

### Option 2: Textual (Full TUI)

Full app framework with DOM-like widget tree, CSS-like `.tcss` styling, reactive attributes, async-first architecture. Rich built-in widget library (buttons, labels, tables, progress bars, tabs, trees, text areas).

**Worker API** for threading (relevant for audio/transcription):
```python
@work(exclusive=True, thread=True)
def transcribe(self, audio):
    result = whisper_engine.transcribe(audio)
    self.call_from_thread(self.update_result, result)
```

**Effort**: Significant. Must restructure around Textual's async event loop. Full-screen takeover. Could conflict with existing threading model (state_manager, audio_recorder, hotkey_listener all own threads).

### Option 3: Rich Now, Textual Later

Start with Rich for pretty output. Rich knowledge transfers directly to Textual. Move to Textual when/if a full interactive TUI is needed.

### Option 4: prompt_toolkit

Strong for interactive input (autocomplete, history, key bindings). Less useful for display-heavy apps. Used by IPython, pgcli, AWS CLI v2.

### Comparison

| Feature | Rich | Textual | prompt_toolkit |
|---------|------|---------|----------------|
| Incremental adoption | Excellent | Poor (all-or-nothing) | Moderate |
| Widget system | No (renderables) | Yes (extensive) | Basic |
| Thread-safe updates | Live is thread-safe | call_from_thread() | Limited |
| Dynamic updates | Live + update() | Reactive attributes | Buffer invalidation |
| Full-screen takeover | Optional (screen=True) | Always | Optional |
| Learning curve | Very low | Medium | Medium |

### Notable Python Apps with Textual TUIs

- **Toad**: Terminal front-end for AI coding tools (Claude Code, Gemini CLI)
- **Posting**: Terminal API client (like Postman)
- **Toolong**: Log file viewer/tailer
- **Memray**: Memory profiler (Bloomberg)
- **Harlequin**: Terminal database client

---

## Integration Patterns (Adding TUI to Existing App)

For an app like Whisper Key that currently uses `print()` and `logging`:

1. **Redirect logging**: custom `logging.Handler` routing to a TUI widget instead of stdout
2. **Redirect stdout/stderr**: replace with file-like objects pointing at TUI panels
3. **Event-driven updates**: business logic emits events through a message queue; UI thread consumes and renders
4. **Thread safety**: all terminal I/O on one thread, cross-thread updates via `call_from_thread()` or message passing
5. **Separate UI from logic**: clean boundary between state management and rendering

---

## Terminal Input Fundamentals

Three terminal modes: **cooked** (line-buffered, OS handles editing), **cbreak** (char-at-a-time, signals still work), **raw** (app gets everything). Arrow/function keys arrive as multi-byte escape sequences needing timeout-based parsing. Mouse tracking via modes 1000-1003 with SGR encoding (mode 1006) preferred.

---

## Recommendation Path for Whisper Key

**Immediate**: Rich for logging + status display (minimal effort, big visual upgrade)
**Later**: Textual if a full interactive TUI with settings control, model selection, and real-time status is desired

Rich gives you colored logging, live status panels, progress bars for model downloads, and tables for settings -- all without restructuring the app. The `RichHandler` drop-in for Python logging is essentially zero-effort.

---

*Sources: Claude Code internals, Sidecar/Crush/Codex/Gemini/Aider GitHub repos, Bubble Tea/Ratatui/Textual/Rich/Ink docs, Charmbracelet ecosystem, DeepWiki architecture analyses, terminal escape code references*
