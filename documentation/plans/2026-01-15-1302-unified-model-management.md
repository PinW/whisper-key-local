# Unified Model Management Implementation Plan

As a *User* I want **all whisper models managed through a unified config system** so I can easily add custom models, HuggingFace models, and local models without code changes.

## Current State Analysis

**What exists (on model-cache-rework branch):**
- `model_cache_overrides` dict in config for non-Systran cache folder mappings
- `WhisperEngine` accepts `model_cache_overrides` parameter
- `_get_model_cache_folder()` method checks overrides before using default prefix
- Hardcoded model menu items in `system_tray.py`
- Model validation removed from `config_manager.py` (faster-whisper handles it)

**Current limitations:**
- Model list is hardcoded in `system_tray.py` (lines 155-166)
- Adding a new model requires code changes in multiple places
- No support for user-defined custom models
- Cache folder overrides are separate from model definitions
- No way to specify HuggingFace paths or local paths for models

**Current config structure:**
```yaml
whisper:
  model_size: base
  model_cache_overrides:
    large: models--Systran--faster-whisper-large-v3
    large-v3-turbo: models--mobiuslabsgmbh--faster-whisper-large-v3-turbo
```

## Target Config Structure

```yaml
whisper:
  model_size: base
  device: cpu
  compute_type: int8
  language: auto
  beam_size: 5

  # Available models (set enabled: false to hide from menu)
  # HuggingFace models are cached at: ~/.cache/huggingface/hub
  models:
    # Official whisper models
    tiny:
      label: "Tiny (76MB, fastest)"
      group: official
      enabled: true
    base:
      label: "Base (145MB, balanced)"
      group: official
      enabled: true
    small:
      label: "Small (484MB, accurate)"
      group: official
      enabled: true
    medium:
      label: "Medium (1.5GB, very accurate)"
      group: official
      enabled: true
    large: # Uses the large-v3 version
      label: "Large (3.1GB, best accuracy)"
      group: official
      enabled: true
    large-v3-turbo: # 8x faster and only slightly less accurate (transcription optimized)
      label: "Large-V3-Turbo (1.6GB, newest)"
      group: official
      enabled: true

    # Models with native faster-whisper support
    tiny.en:
      label: "Tiny.En (English)"
      group: custom
      enabled: true
    base.en:
      label: "Base.En (English)"
      group: custom
      enabled: true
    small.en:
      label: "Small.En (English)"
      group: custom
      enabled: true
    medium.en:
      label: "Medium.En (English)"
      group: custom
      enabled: true
    distil-large-v3.5: # About 1.5x faster than large-v3-turbo
      source: distil-whisper/distil-large-v3.5-ct2
      label: "Distil-Large-V3.5 (English)"
      group: custom

    # Custom models (must be CTranslate2 format)
    # huggingface-model:
    #   source: huggingface-username/whisper-model-ct2
    #   label: "HuggingFace Model"
    #   group: custom
    # local-model:
    #   source: C:/Models/whisper-custom-ct2
    #   label: "Local Whisper Model"
    #   group: custom
```

## Implementation Plan

### Phase 1: Model Registry Class
- [ ] Create `ModelRegistry` class in new file `model_registry.py`
- [ ] Parse models from config into structured format
- [ ] Implement source type detection:
  - No `source` key → use model key as faster-whisper short name
  - `source` contains `/` and path exists locally → local path
  - `source` contains `/` but not local → HuggingFace path
  - `source` without `/` → faster-whisper short name
- [ ] Implement cache folder derivation:
  - HuggingFace path: `user/repo` → `models--user--repo`
  - Short name: use faster-whisper's internal `_MODELS` mapping or default prefix
  - Local path: no cache folder needed
- [ ] Method to get model by key
- [ ] Method to get models by group
- [ ] Method to get all model keys

### Phase 2: Update WhisperEngine
- [ ] Replace `model_cache_overrides` parameter with `model_registry` parameter
- [ ] Update `_load_model()` to get source from registry
- [ ] Update `_load_model_async()` to get source from registry
- [ ] Pass actual source (not key) to `WhisperModel()`

### Phase 3: Update System Tray
- [ ] Remove hardcoded model menu items
- [ ] Get models from registry, grouped by `group` field
- [ ] Build menu dynamically with separators between groups
- [ ] Order groups: official → custom
- [ ] Use model key for selection, label for display

### Phase 4: Update Config and Main
- [ ] Add default `models` section to `config.defaults.yaml`
- [ ] Remove `model_cache_overrides` section (replaced by `models`)
- [ ] Update `main.py` to create `ModelRegistry` from config
- [ ] Pass registry to `WhisperEngine` and `SystemTray`

### Phase 5: Move Cache Management to ModelRegistry
- [ ] Add `get_hf_cache_path()` method to ModelRegistry (base HuggingFace cache directory)
- [ ] Add `is_model_cached(key)` method to ModelRegistry
- [ ] Remove `_get_model_cache_folder()` from WhisperEngine (use registry instead)
- [ ] Remove `_is_model_cached()` from WhisperEngine (use registry instead)
- [ ] Update WhisperEngine to call registry for cache checks

### Phase 6: Testing and Edge Cases (prompt user to test)
- [ ] Test official models (short names)
- [ ] Test HuggingFace path models (distil-large-v3.5)
- [ ] Test local path models
- [ ] Test cache detection for all types
- [ ] Test adding custom model via user config
- [ ] Test invalid model handling

## Implementation Details

### ModelRegistry Class

```python
import os
from faster_whisper.utils import _MODELS

class ModelRegistry:
    DEFAULT_CACHE_PREFIX = "models--Systran--faster-whisper-"

    def __init__(self, models_config: dict):
        self.models = {}
        for key, config in models_config.items():
            self.models[key] = ModelDefinition(key, config)

    def get_model(self, key: str) -> ModelDefinition:
        return self.models.get(key)

    def get_source(self, key: str) -> str:
        model = self.get_model(key)
        return model.source if model else key

    def get_cache_folder(self, key: str) -> str:
        model = self.get_model(key)
        if not model:
            return f"{self.DEFAULT_CACHE_PREFIX}{key}"
        return model.cache_folder

    def get_models_by_group(self, group: str) -> list:
        return [m for m in self.models.values() if m.group == group and m.enabled]

    def get_groups_ordered(self) -> list:
        return ["official", "custom"]

    def get_hf_cache_path(self) -> str:
        userprofile = os.environ.get('USERPROFILE')
        if userprofile:
            return os.path.join(userprofile, '.cache', 'huggingface', 'hub')
        return os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')

    def is_model_cached(self, key: str) -> bool:
        model = self.get_model(key)
        if model and model.is_local_path:
            return True  # Local paths are always "cached"
        cache_folder = self.get_cache_folder(key)
        if not cache_folder:
            return False
        return os.path.exists(os.path.join(self.get_hf_cache_path(), cache_folder))


class ModelDefinition:
    def __init__(self, key: str, config: dict):
        self.key = key
        self.source = config.get("source", key)
        self.label = config.get("label", key.title())
        self.group = config.get("group", "custom")
        self.enabled = config.get("enabled", True)
        self.is_local_path = self._check_is_local_path()
        self.cache_folder = self._derive_cache_folder()

    def _check_is_local_path(self) -> bool:
        if self.source.startswith("\\\\") or (len(self.source) > 2 and self.source[1] == ":"):
            return True
        if "/" in self.source:
            return os.path.exists(self.source)
        return False

    def _derive_cache_folder(self) -> str:
        if self.is_local_path:
            return None

        if "/" in self.source:
            # HuggingFace path: user/repo → models--user--repo
            return "models--" + self.source.replace("/", "--")

        # Check faster-whisper's short name mapping
        if self.source in _MODELS:
            repo = _MODELS[self.source]
            return "models--" + repo.replace("/", "--")

        return f"{ModelRegistry.DEFAULT_CACHE_PREFIX}{self.source}"
```

### Source Type Detection Logic

```
Input: model source string
│
├─ Starts with C:\ or \\ ? (Windows absolute path)
│   └─ YES → LOCAL PATH (load from disk)
│
├─ Contains "/" ?
│   ├─ YES: Path exists locally?
│   │   ├─ YES → LOCAL PATH (load from disk)
│   │   └─ NO  → HUGGINGFACE PATH (download from HF)
│   └─ NO → SHORT NAME (use faster-whisper built-in)
```

### Cache Folder Derivation

| Source Type | Example Source | Cache Folder |
|-------------|----------------|--------------|
| Short name | `tiny` | `models--Systran--faster-whisper-tiny` |
| Short name (non-Systran) | `large-v3-turbo` | `models--mobiuslabsgmbh--faster-whisper-large-v3-turbo` |
| HuggingFace path | `distil-whisper/distil-large-v3.5-ct2` | `models--distil-whisper--distil-large-v3.5-ct2` |
| Local path | `C:\Models\my-model` | N/A (direct load) |

## Files to Modify

| File | Changes |
|------|---------|
| `model_registry.py` | **NEW FILE** - ModelRegistry and ModelDefinition classes |
| `whisper_engine.py` | Replace `model_cache_overrides` with `model_registry`, update cache/load methods |
| `system_tray.py` | Remove hardcoded menu, build from registry |
| `main.py` | Create ModelRegistry, pass to components |
| `config.defaults.yaml` | Add `models` section, remove `model_cache_overrides` |

## Success Criteria

- [ ] All existing models work without changes to user config
- [ ] System tray menu is built dynamically from config
- [ ] Adding a new HuggingFace model only requires config change
- [ ] Adding a local model only requires config change
- [ ] Cache detection works correctly for all model types
- [ ] Model groups are displayed with separators in tray menu
- [ ] Invalid model sources show helpful error messages