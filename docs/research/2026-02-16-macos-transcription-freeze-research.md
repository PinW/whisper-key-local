# macOS Transcription Freeze & Slowness Research

**Date:** 2026-02-16
**Status:** Research complete, not yet investigated on device

## Bug Reports

### 1. System Freezes on Transcription (Roadmap Bug)
From `roadmap.md`: *"(macOS) System freezes on transcription - needs verification"*

### 2. Very Slow Transcription (User Report)
User experienced very slow transcription on macOS while Zwift (3D cycling game) was running.

---

## Architecture Analysis

### Threading Model

The application uses multiple threads on macOS:

| Thread | Purpose | Key Constraint |
|--------|---------|----------------|
| **Main thread** | NSApplication event loop (`app.run_event_loop`) | Must run Cocoa run loop for macOS events to be delivered |
| **pystray thread** | System tray icon (via `run_detached`) | Spawned by pystray internally |
| **Recording thread** | `AudioRecorder._record_audio` — sounddevice InputStream | Daemon thread, started per-recording |
| **Hotkey callbacks** | Each hotkey press spawns a new daemon thread via `threading.Thread(target=binding.press_callback)` | Spawned from NSEvent handler on main thread |
| **Audio feedback** | Sound playback via playsound3 | Daemon thread per sound |
| **VAD event dispatch** | `ContinuousVoiceDetector._dispatch_event` | Daemon thread per event |

### macOS Event Flow

```
Main thread
  app.setup()                          # NSApplication.sharedApplication()
  ...component init...
  app.run_event_loop(shutdown_event)   # Polls NSApp.nextEventMatchingMask_ every 0.1s
       |
       v
  NSEvent global monitor (_handle_event)  # Called on main thread by Cocoa
       |
       v
  threading.Thread(target=binding.press_callback).start()  # Spawns callback thread
       |
       v
  state_manager.toggle_recording() or stop_recording()
       |
       v
  _transcription_pipeline() runs on CALLBACK THREAD (not main thread)
       |
       +---> audio_feedback.play_stop_sound()     # spawns another thread
       +---> whisper_engine.transcribe_audio()     # CPU-intensive, runs on callback thread
       +---> clipboard_manager.deliver_transcription()  # Quartz CGEventPost for paste
```

### Key macOS Platform Constraints

1. **NSApplication event loop must run on main thread** (`app.py` line 17-27): The main thread runs `run_event_loop()` which polls `nextEventMatchingMask_` every 100ms.

2. **NSEvent global monitor handlers are called on the main thread** (Apple docs): The `_handle_event` function in `hotkeys.py` is invoked on the main thread by Cocoa's run loop.

3. **Hotkey callbacks spawn new threads** (`hotkeys.py` lines 108, 135): `threading.Thread(target=binding.press_callback, daemon=True).start()` ensures callbacks don't block the main thread's event loop.

4. **Quartz keyboard simulation** (`keyboard.py`): `CGEventPost(kCGHIDEventTap, event)` is used for paste simulation - this should work from any thread but is called from the callback thread during transcription pipeline.

---

## Hypothesis 1: The Freeze

### Root Cause: Main Thread Starvation During Transcription Is Unlikely

The initial hypothesis was that transcription blocks the main thread. However, analysis shows this is **not** the case:

- The hotkey handler in `hotkeys.py` dispatches callbacks to **new daemon threads** (lines 108, 135)
- `_transcription_pipeline()` runs on the spawned callback thread
- The main thread continues its 100ms polling loop in `app.run_event_loop()`
- CTranslate2 releases the GIL during inference, so even if the callback thread is CPU-bound, the main thread's GIL acquisition for the event loop poll should not be blocked for extended periods

### More Likely Freeze Causes

**A. CPU Saturation (All Cores Busy)**

CTranslate2 uses OpenMP (or BS::thread_pool on macOS ARM64) for intra-op parallelism. By default, it may use **all available CPU cores** for transcription. If the system has limited cores (e.g., MacBook Air M1 with 4 performance + 4 efficiency cores), transcription can saturate all cores, making the entire macOS system unresponsive, not just the app.

This would explain "system freezes" rather than "app freezes" - it's a system-wide CPU starvation issue.

**B. Memory Pressure**

Whisper models consume significant RAM:
- `tiny`: ~75 MB
- `small`: ~500 MB
- `medium`: ~1.5 GB
- `large-v3`: ~3 GB

If the system is already under memory pressure (e.g., Xcode open), loading or running the model could trigger swap thrashing, causing system-wide slowdown that appears as a freeze.

**C. NSEvent Handler Running Synchronous Work**

Although callbacks are dispatched to threads, the `_handle_event` function itself is called on the main thread. If there's ever a case where the callback blocks before the thread dispatch (e.g., exception handling, logging I/O), it could momentarily block the event loop. This is a minor risk but worth checking.

---

## Hypothesis 2: The Slowness

### Root Cause: Resource Contention with Zwift

The user experienced slow transcription specifically **with Zwift running**. Zwift is a 3D cycling/running game that's both GPU and CPU intensive. This is almost certainly caused by:

**A. CPU Competition**

Zwift's 3D rendering, physics simulation, and networking consume significant CPU. CTranslate2's inference then competes for the same CPU cores, dramatically increasing transcription time.

On CPU mode (which is the default and most common on macOS), faster-whisper's transcription time is directly proportional to available CPU. If Zwift is consuming 50-80% of CPU, transcription that normally takes 2-3 seconds could take 10-15 seconds.

**B. Memory Pressure and Swap**

Zwift typically uses 2-4 GB of RAM plus GPU memory. Combined with the Whisper model in memory, this can push the system into memory pressure, causing page faults and disk I/O during inference.

**C. Thermal Throttling**

MacBooks aggressively thermal throttle. If Zwift has already heated up the CPU/GPU, the system may be running at reduced clock speeds when transcription starts. This is especially relevant since Zwift keeps thermals elevated continuously during a ride.

---

## Are the Freeze and Slowness Related?

**Yes, they share the same underlying mechanism: CPU/resource saturation.**

The difference is degree:
- **Slowness**: Moderate resource contention (e.g., Zwift running) means transcription takes longer but completes
- **Freeze**: Severe resource contention (e.g., CTranslate2 using all cores + other apps) means the system becomes unresponsive

Both stem from CTranslate2 consuming as many CPU resources as it can get, without being constrained.

---

## Investigation Steps

### Step 1: Confirm CPU Saturation Theory
- Run the app on macOS and trigger transcription
- Monitor `Activity Monitor` during transcription: check CPU usage for `python`/`whisper-key` process
- Note: CTranslate2's threads show as part of the Python process
- Check if CPU usage spikes to 400-800% (multi-core)

### Step 2: Check CTranslate2 Thread Count
- Print or log `os.cpu_count()` at startup
- Check if `OMP_NUM_THREADS` is set
- Inspect CTranslate2's actual thread usage during transcription

### Step 3: Test with Controlled CPU Load
- Run transcription with nothing else open (baseline)
- Run transcription with Zwift running
- Compare transcription times

### Step 4: Test Thread Limiting
- Set `OMP_NUM_THREADS=2` (or half of cores) and test if freeze disappears
- Configure CTranslate2's `cpu_threads` parameter when creating WhisperModel

### Step 5: Verify Main Thread Responsiveness
- Add timing instrumentation to `app.run_event_loop` to log if any event loop iteration takes >200ms
- This confirms whether the main thread itself is actually blocked

---

## Potential Fixes

### Fix 1: Limit CTranslate2 CPU Threads (Recommended First Step)

WhisperModel accepts `cpu_threads` parameter. Setting this to half the available cores prevents system saturation:

```python
import os
cpu_threads = max(1, os.cpu_count() // 2)

self.model = WhisperModel(
    model_source,
    device=self.device,
    compute_type=self.compute_type,
    cpu_threads=cpu_threads
)
```

Trade-off: Slightly slower transcription in isolation, but prevents system freezes and maintains responsiveness.

### Fix 2: Set OMP_NUM_THREADS Environment Variable

A simpler approach - set at startup before CTranslate2 is loaded:

```python
import os
os.environ.setdefault('OMP_NUM_THREADS', str(max(1, os.cpu_count() // 2)))
```

### Fix 3: Lower Process Priority (Nice Value)

On macOS, set the process to lower priority so it yields to interactive apps:

```python
import os
os.nice(10)  # Lower priority (higher nice value)
```

### Fix 4: Use multiprocessing Instead of Threading for Transcription

Run `whisper_engine.transcribe_audio()` in a separate **process** (not thread). This provides complete isolation:
- The transcription process can be CPU-limited independently
- The main process event loop is never affected by GIL contention
- Can set CPU affinity on the child process

This is the most robust fix but adds complexity (IPC for audio data and results).

### Fix 5: Make Thread Count Configurable

Add a `cpu_threads` setting to `config.defaults.yaml` under the `whisper` section, defaulting to `auto` (half cores) but allowing users to tune it.

---

## Recommended Next Steps

1. **Quick win**: Add `cpu_threads` parameter to `WhisperModel` initialization in `whisper_engine.py`, defaulting to half of `os.cpu_count()`. This is a one-line change with high impact.

2. **Verify on device**: Test on macOS with and without the fix. Measure transcription time and system responsiveness.

3. **Make configurable**: Add `cpu_threads` to the whisper config section so users can tune the trade-off between transcription speed and system responsiveness.

4. **Consider process priority**: Add `os.nice(10)` to `main.py` on macOS to make the app yield to interactive applications.

5. **Update roadmap bug**: Change from "needs verification" to documented root cause once confirmed on device.

---

## Sources

- [Apple: addGlobalMonitorForEvents(matching:handler:)](https://developer.apple.com/documentation/appkit/nsevent/addglobalmonitorforevents(matching:handler:)) - documents handler is called on main thread
- [Apple: Monitoring Events](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/EventOverview/MonitoringEvents/MonitoringEvents.html) - confirms handlers always called on main thread
- [Apple: NSApplication](https://developer.apple.com/documentation/appkit/nsapplication) - main event loop must run on main thread
- [Apple: Thread Safety Summary](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/Multithreading/ThreadSafetySummary/ThreadSafetySummary.html) - AppKit thread safety constraints
- [CTranslate2: Multithreading and parallelism](https://opennmt.net/CTranslate2/parallel.html) - GIL release during inference, thread configuration
- [CTranslate2 GitHub](https://github.com/OpenNMT/CTranslate2) - OpenMP/BS::thread_pool for parallelism
- [pystray FAQ](https://pystray.readthedocs.io/en/latest/faq.html) - macOS main thread requirement, run_detached
- [pystray run_detached macOS issue #138](https://github.com/moses-palmer/pystray/issues/138) - macOS-specific threading
- [PyObjC threading helpers](https://pyobjc.readthedocs.io/en/latest/api/threading-helpers.html) - safe threading methods
