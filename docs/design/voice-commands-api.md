# Voice Commands API

## Vision

Local voice commands already support shell commands, hotkeys, and text snippets. Extend them with a local API so other apps can register triggers, receive transcriptions, and handle commands.

## Local API Server

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

### Protocol

- WebSocket message format and types
- Registration and command notification flows
- Error handling
- Authentication for the local API
- Priority/conflict resolution when multiple plugins want the same phrase
- Handling partial matches during streaming

### Plugin Architecture

- External processes connecting via API, or scripts/configs within Whisper Key?
- Discovery and registration mechanism
- Lifecycle management: startup, shutdown, crash recovery

### Reconnection

- Persist registered triggers across restarts, or require plugins to re-register?
- Re-registration is simpler but requires plugins to track their own config
