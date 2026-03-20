# Implementation Log

## Branch: feature/vad-realtime-wakeword
## Basis: local_master (7625b56)

### Phase 0: Listening Mode System — DONE (dcc1b05)
- 7 Dateien modifiziert, ListeningMode Enum, HTTP /mode/*, CLI --mode/--preview, Tray Radiobuttons
### Phase 1: Audio-Stream Refactoring — DONE (c6b46db)
- Neue audio_stream.py (AudioStreamManager), audio_recorder.py refactored, state_manager vereinfacht
### Phase 2+3: Continuous Listening + Realtime Preview — DONE (211162a)
- continuous_listener.py (VAD state machine, pre-buffer, min/max guards)
- realtime_preview.py (timer-driven, single-model, transcribe_lock)
- Integration in StateManager + main.py
### Phase 4: Wake Word Detection — PENDING
