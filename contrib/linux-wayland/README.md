# Linux/Wayland Client Scripts for HTTP Trigger

Shell scripts to control whisper-key remotely from a Linux/Wayland desktop via the HTTP trigger API.

## Use Case

Run whisper-key on a host with GPU (e.g. Windows with NVIDIA), control it from a Linux machine
(e.g. a VM, another PC on the network, or WSL). The scripts call the HTTP API, copy the
transcribed text to the Wayland clipboard, and auto-paste it with a simulated Ctrl+V.

```
[Linux Client] --HTTP--> [whisper-key Host :5757] --Microphone--> [Whisper GPU]
     |                                                                  |
     |<--JSON (transcribed text)----------------------------------------|
     |
     wl-copy -> ydotool Ctrl+V -> text pasted
```

## Scripts

| Script | Description |
|---|---|
| `whisper-toggle` | Toggle: start recording if idle, stop + transcribe + paste if recording |
| `whisper-record` | Start recording only |
| `whisper-stop` | Stop recording + transcribe + paste |
| `whisper-cancel` | Cancel ongoing recording |

## Installation

```bash
# Copy scripts to your PATH
cp whisper-* ~/.local/bin/
chmod +x ~/.local/bin/whisper-*

# Install dependencies (Arch Linux)
sudo pacman -S curl jq wl-clipboard ydotool libnotify

# Start ydotool daemon (needed for Ctrl+V simulation)
sudo systemctl enable --now ydotool
```

## Configuration

Create `~/.config/whisper-key/config`:

```bash
WHISPER_HOST=192.168.1.100   # IP of the whisper-key host (default: localhost)
WHISPER_PORT=5757            # HTTP trigger port (default: 5757)
SOUND_ENABLED=true           # Play sound feedback (default: true)
NOTIFY_ENABLED=true          # Show desktop notifications (default: true)
```

## Keyboard Shortcut

Bind `whisper-toggle` to a hotkey for hands-free use. Example for GNOME:

```bash
# Settings > Keyboard > Custom Shortcuts, or via CLI:
CUSTOM_SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
KEY_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/whisper/"

gsettings set "${CUSTOM_SCHEMA}:${KEY_PATH}" name "Whisper Toggle"
gsettings set "${CUSTOM_SCHEMA}:${KEY_PATH}" command "$HOME/.local/bin/whisper-toggle"
gsettings set "${CUSTOM_SCHEMA}:${KEY_PATH}" binding "<Control>space"
```

## Dependencies

- `curl`, `jq` — HTTP requests + JSON parsing
- `wl-clipboard` (wl-copy) — Wayland clipboard
- `ydotool` + `ydotoold` — key simulation (Ctrl+V) under Wayland
- `libnotify` (notify-send) — desktop notifications
- `libcanberra` (paplay) — sound feedback (optional)
