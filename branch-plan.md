# Whisper.cpp Migration Plan
*Branch: whisper-cpp*

## Goal
Migrate from faster-whisper to whisper.cpp for improved performance and lower memory usage.

## Expected Benefits
- 20-40% faster inference time
- 30-50% lower memory usage during idle
- Better CPU optimization (SIMD, threading)
- More responsive hotkey experience

## Migration Steps

### 1. Research & Setup
- [ ] Selected pywhispercpp from git+https://github.com/absadiki/pywhispercpp
- [ ] Investigate build dependencies (C++ compiler requirements)
- [ ] Document any necessary build tools in README.md
- [ ] Update requirements.txt with pywhispercpp dependency
- [ ] Remove faster-whisper dependency

### 2. Code Changes
- [ ] Implement model downloader for GGML model files (.bin)
- [ ] Rewrite `_load_model` method to handle local model paths
- [ ] Update WhisperEngine class to use pywhispercpp bindings
- [ ] Modify model loading logic (constructor vs transcribe parameters)
- [ ] Update transcription method to handle new output format
- [ ] Handle any API differences

### 3. Configuration Updates
- [ ] Map existing config parameters to pywhispercpp API
- [ ] Handle device/compute_type parameter differences
- [ ] Update cpu_threads mapping to PyWhisperCpp constructor
- [ ] Review config.yaml for any pywhispercpp specific settings
- [ ] Update model size mappings if needed
- [ ] Ensure backward compatibility

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
- [ ] Add a folder at `./documentation/whisper-cpp/` with relevant notes for future dev

## Rollback Plan
We're on a branch, so no problem

## Critical Implementation Notes
**Model Management**: whisper-cpp requires manual GGML model files (.bin) unlike faster-whisper's automatic downloads. Implement model downloader using model_cache_dir from config.yaml.

**API Differences**: Need to research pywhispercpp API for parameter handling and transcription output format.

**Build Dependencies**: pywhispercpp may require C++ compiler if pre-built wheels unavailable.

**Configuration Compatibility**: 
- All parameter mapping handled internally - no config file changes needed

**Audio Processing**: Need to verify if pywhispercpp expects file paths or can handle raw audio arrays.

**Model Download URLs**: GGML models downloaded from https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ - verify these URLs are current and accessible.

**Parameter Verification Needed**: Research pywhispercpp API documentation for exact parameter names and usage patterns.

## Success Criteria
- [ ] App starts faster
- [ ] Lower memory usage during idle
- [ ] Faster transcription times
- [ ] All existing functionality preserved
- [ ] No meaningful regression in accuracy
- [ ] Model downloading works seamlessly