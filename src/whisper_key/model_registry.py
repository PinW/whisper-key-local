import os
from faster_whisper.utils import _MODELS


class ModelRegistry:
    DEFAULT_CACHE_PREFIX = "models--Systran--faster-whisper-"

    def __init__(self, models_config: dict):
        self.models = {}
        for key, config in models_config.items():
            if isinstance(config, dict):
                self.models[key] = ModelDefinition(key, config)

    def get_model(self, key: str):
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
            return os.path.exists(os.path.join(model.source, 'model.bin'))
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
            return "models--" + self.source.replace("/", "--")

        if self.source in _MODELS:
            repo = _MODELS[self.source]
            return "models--" + repo.replace("/", "--")

        return f"{ModelRegistry.DEFAULT_CACHE_PREFIX}{self.source}"
