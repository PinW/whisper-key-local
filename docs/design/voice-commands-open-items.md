# Voice Commands - Open Items

Parking lot for concepts to discuss/design later.

## Protocol Design

Need to work through the WebSocket message protocol details:
- Message format and types
- Registration flow
- Command notification flow
- Error handling

## Plugin Architecture

Clarify what "plugins" mean in this context:
- Are they external processes that connect via API?
- Are they scripts/configs within WK?
- How do they register and discover each other?
- Lifecycle management (startup, shutdown, crash recovery)

## Re-registration on Reconnect

If plugins are external processes connecting via WebSocket:
- Should WK persist registered triggers across restarts?
- Or should plugins re-register every time they connect?
- Stateless (re-register) is simpler but requires plugins to track their own config
