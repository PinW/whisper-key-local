import logging
import os
from typing import Optional

from faster_whisper.utils import _MODELS


class ModelRegistry:
    DEFAULT_CACHE_PREFIX = "models--Systran--faster-whisper-"

    def __init__(self, whisper_models_config: dict = None, streaming_models_config: dict = None):
        self.models = {}
        self.logger = logging.getLogger(__name__)

        if whisper_models_config:
            for key, config in whisper_models_config.items():
                if isinstance(config, dict):
                    self.models[key] = ModelDefinition(key, config, model_type="whisper")

        if streaming_models_config:
            for key, config in streaming_models_config.items():
                if isinstance(config, dict):
                    self.models[key] = ModelDefinition(key, config, model_type="streaming")

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
        if model and model.model_type == "streaming":
            return self._is_streaming_model_cached(key)
        if model and model.is_local_path:
            return os.path.exists(os.path.join(model.source, 'model.bin'))
        cache_folder = self.get_cache_folder(key)
        if not cache_folder:
            return False
        return os.path.exists(os.path.join(self.get_hf_cache_path(), cache_folder))

    def _is_streaming_model_cached(self, key: str) -> bool:
        model = self.get_model(key)
        if not model or not model.files:
            return False

        snapshot_path = self._get_streaming_snapshot_path(key)
        if not snapshot_path:
            return False

        for file_path in model.files.values():
            if not os.path.exists(os.path.join(snapshot_path, file_path)):
                return False
        return True

    def _get_streaming_snapshot_path(self, key: str) -> Optional[str]:
        model = self.get_model(key)
        if not model:
            return None

        model_dir = os.path.join(self.get_hf_cache_path(), model.cache_folder)
        snapshots_dir = os.path.join(model_dir, 'snapshots')

        if not os.path.exists(snapshots_dir):
            return None

        snapshots = os.listdir(snapshots_dir)
        if not snapshots:
            return None

        return os.path.join(snapshots_dir, snapshots[0])

    def get_streaming_model_path(self, key: str) -> Optional[tuple]:
        model = self.get_model(key)
        if not model or model.model_type != "streaming":
            return None

        if not self._is_streaming_model_cached(key):
            if not self.download_streaming_model(key):
                return None

        snapshot_path = self._get_streaming_snapshot_path(key)
        if not snapshot_path:
            return None

        return snapshot_path, model.files

    def download_streaming_model(self, key: str) -> bool:
        model = self.get_model(key)
        if not model or model.model_type != "streaming":
            return False

        try:
            from huggingface_hub import snapshot_download
            self.logger.info(f"Downloading streaming model: {model.source}")
            print(f"   Downloading streaming model: {model.label}...")
            snapshot_download(repo_id=model.source)
            self.logger.info(f"Streaming model downloaded: {model.source}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to download streaming model {model.source}: {e}")
            return False


class ModelDefinition:
    def __init__(self, key: str, config: dict, model_type: str = "whisper"):
        self.key = key
        self.model_type = model_type
        self.source = config.get("source", key)
        self.label = config.get("label", key.title())
        self.group = config.get("group", "custom")
        self.enabled = config.get("enabled", True)
        self.files = config.get("files", {})
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
