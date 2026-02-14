# Voice Commands Vision

## Overview

Build on streaming STT to enable voice-controlled actions, starting simple and evolving into an extensible API platform.

## Phase 1: Built-in Commands

Basic prototype focused on window/application control:

- Switch between open windows
- Switch between applications
- Minimize/maximize/close windows

Detection approach: keyword/phrase matching on streaming transcription.

## Phase 2: Custom Commands

User-configurable commands that trigger:

- Bash/shell commands
- Launch programs
- Keyboard shortcuts
- Custom scripts

Config-driven (YAML) command definitions with trigger phrases.

## Phase 3: Local API Server

Transform Whisper Key into a voice command platform:

```
┌─────────────────────────────────────────────────────┐
│                   Whisper Key                        │
│  ┌─────────────┐    ┌──────────────────────────┐   │
│  │ Streaming   │───▶│ Local API Server         │   │
│  │ Recognizer  │    │ (localhost:PORT)         │   │
│  └─────────────┘    └──────────────────────────┘   │
│                              │                      │
└──────────────────────────────│──────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ External App  │    │ External App  │    │ External App  │
│ (Plugin A)    │    │ (Plugin B)    │    │ (Plugin C)    │
└───────────────┘    └───────────────┘    └───────────────┘
```

### API Capabilities

External apps can:

1. **Subscribe to voice stream** - receive real-time transcription
2. **Register trigger phrases** - claim keywords/phrases for their commands
3. **Cancel transcription** - intercept and prevent text paste when handling a command
4. **Report command status** - feedback to user (success/failure)

### Protocol Ideas

- WebSocket for real-time streaming
- REST endpoints for registration/configuration
- JSON message format

### Example Flow

1. User says: "launch spotify"
2. Streaming recognizer transcribes in real-time
3. API server detects "launch" keyword
4. Connected music plugin claims the command
5. Plugin signals "cancel transcription"
6. Plugin launches Spotify
7. User sees feedback (sound/notification)

## Open Questions

- Authentication for local API? (probably unnecessary for localhost)
- Priority/conflict resolution when multiple plugins want same phrase?
- How to handle partial matches during streaming?
- Plugin discovery/registration mechanism?
