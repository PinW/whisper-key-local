# Audio Sources TODO

1. Fix errors with WASAPI devices so standard input sources enumerate and record without exceptions.
2. Fix errors with WDM-KS devices to ensure they can be selected and used reliably.
3. After WASAPI input works, expose loopback devices in the source list and verify they capture playback audio without errors.

## Notes Learned Today

- Loopback devices become visible on Windows when dropping in Audacity’s bundled PortAudio DLL (tested with ~v3.6.3), but the same runtime errors still occur when selecting/using them in Whisper Key.
- Audacity itself (including v3.7.5) shows and records loopback sources successfully, so the DLLs are capable; the failure is likely in our integration or the `sounddevice` layer.
- The latest precompiled PortAudio DLLs (master builds, Audacity 3.7.5) still hide WASAPI loopback devices for us, reinforcing that we need to debug `sounddevice` usage or raise an issue upstream.
- If progress stalls, consider posting details to the `sounddevice` project and/or adding a PyAudio backend option, with a config switch letting users choose the input stack for stubborn setups.
