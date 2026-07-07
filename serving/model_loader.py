from __future__ import annotations

import os
import time
from dataclasses import dataclass
from threading import Lock

import mlflow
import mlflow.sklearn


@dataclass
class LoadedModel:
    model: object
    uri: str
    loaded_at: float


class RegistryModelLoader:
    def __init__(self, model_uri: str | None = None, reload_seconds: int | None = None) -> None:
        self.model_uri = model_uri or os.getenv("MODEL_URI", "models:/NewsClassifier/Production")
        self.reload_seconds = reload_seconds or int(os.getenv("MODEL_RELOAD_SECONDS", "30"))
        self._loaded: LoadedModel | None = None
        self._lock = Lock()
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))

    def get_model(self):
        now = time.time()
        with self._lock:
            if self._loaded is None or now - self._loaded.loaded_at >= self.reload_seconds:
                model = mlflow.sklearn.load_model(self.model_uri)
                self._loaded = LoadedModel(model=model, uri=self.model_uri, loaded_at=now)
            return self._loaded.model

    def reload(self) -> str:
        with self._lock:
            model = mlflow.sklearn.load_model(self.model_uri)
            self._loaded = LoadedModel(model=model, uri=self.model_uri, loaded_at=time.time())
            return self.model_uri
