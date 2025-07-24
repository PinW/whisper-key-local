# Whisper.cpp Migration Plan
*Branch: whisper-cpp*

**NOTE: Execute one task at a time with explanations for beginner coder.**
**NOTE: Update this file by checking off tasks as they are completed.**

## Goal
Migrate from faster-whisper to whisper.cpp for improved performance and lower memory usage.

## Expected Benefits
- 20-40% faster inference time
- 30-50% lower memory usage during idle
- Better CPU optimization (SIMD, threading)
- More responsive hotkey experience

## Migration Steps

### 1. Research & Setup
- [x] Get latest documentation for whispercpp and write to folder `.documentation/whispercpp`
- [x] Download latest documentation for pywhispercpp `.documentation/pywhispercpp`
- [x] Update this plan based on documentation
- [x] Selected pywhispercpp from git+https://github.com/absadiki/pywhispercpp
- [x] Use pre-built wheels: `pip install git+https://github.com/absadiki/pywhispercpp`
- [x] Document installation method (pre-built wheels available, C++ only for GPU builds)  
- [x] Update requirements.txt with pywhispercpp dependency
- [x] Remove faster-whisper dependency

### 2. Code Changes
- [x] Models auto-download (no manual implementation needed)
- [x] Update Model constructor: `Model(model="tiny", n_threads=config_value, **params)`
- [x] Map config `cpu_threads` to Model constructor `n_threads` parameter
- [x] Update transcription method to handle Segment objects (.text, .start, .end)
- [x] Remove device/compute_type parameter handling (not used in pywhispercpp)
- [x] Handle API differences: Segment objects instead of dict output

### 3. Configuration Updates
- [x] Map existing config parameters to pywhispercpp API
- [x] Remove device/compute_type parameters (not supported)
- [x] Map cpu_threads config to n_threads Model parameter
- [x] Model sizes unchanged (tiny, base, small, medium, large)
- [x] No model download config needed (auto-handled by library)
- [x] Ensure backward compatibility for user-facing config

### 4. Testing & Validation
- [ ] Create isolated component test for pywhispercpp
- [ ] Test model downloading and loading functionality
- [ ] Test model loading performance with timing decorators
- [ ] Verify transcription accuracy with side-by-side comparison
- [ ] Measure memory usage improvements with benchmarking
- [ ] Test all model sizes (tiny, base, small)
- [ ] Validate hotkey responsiveness
- [ ] Perform regression testing against faster-whisper results

### 5. Documentation
- [ ] Update `./documentation/components.md`

## Rollback Plan
We're on a branch, so no problem

## Critical Implementation Notes
**API Differences**: CONFIRMED & IMPLEMENTED
- Constructor: `Model(model="tiny", n_threads=6, **params)`
- Transcribe: `transcribe(media_file, **params)` returns Segment objects
- Segment objects have: `.text`, `.start`, `.end` attributes
- No device/compute_type parameters

**Build Dependencies**: CONFIRMED
- Pre-built wheels available via `pip install git+https://github.com/absadiki/pywhispercpp`
- C++ compiler only needed for GPU acceleration builds

**Configuration Compatibility**: CONFIRMED & IMPLEMENTED
- Map cpu_threads → n_threads (Model constructor) ✅ Done in main.py:104
- Remove device/compute_type (not supported) ✅ Done in config.yaml & config_manager.py
- Model sizes unchanged ✅ Confirmed working

**Audio Processing**: CONFIRMED
- Accepts both file paths AND raw numpy arrays
- No conversion needed for existing audio handling

**Model Download**: CONFIRMED
- Auto-download on first use to configurable directory
- Uses GGML format from huggingface.co/ggerganov/whisper.cpp
- No manual implementation needed

## Next Steps for Testing
When resuming work, focus on Section 4 (Testing & Validation):
1. Create isolated pywhispercpp component test
2. Verify model downloading works
3. Performance benchmarking vs faster-whisper
4. Regression testing for accuracy

## Success Criteria
- [ ] App starts faster
- [ ] Lower memory usage during idle
- [ ] Faster transcription times
- [ ] All existing functionality preserved
- [ ] No meaningful regression in accuracy
- [ ] Model downloading works seamlessly