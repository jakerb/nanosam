"""Wake word detection using openWakeWord."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from loguru import logger


class WakeWordDependencyError(RuntimeError):
    """Raised when wake word dependencies are missing."""


def _load_openwakeword_model(model_paths: list[str] | None):
    try:
        from openwakeword.model import Model
    except Exception as e:  # pragma: no cover - import error path
        raise WakeWordDependencyError(
            "openwakeword is required for wake word detection. "
            "Install with: pip install 'nanobot-ai[voice]'"
        ) from e

    if model_paths:
        resolved = [str(Path(p).expanduser()) for p in model_paths]
        return Model(wakeword_models=resolved)
    return Model()


def _normalize_keyword(name: str) -> str:
    return name.strip().lower().replace("_", " ")


@dataclass
class WakeWordConfig:
    wake_word: str
    model_paths: list[str] | None
    threshold: float
    cooldown_s: float


class WakeWordDetector:
    """Detect wake word from 16kHz int16 PCM frames."""

    def __init__(self, config: WakeWordConfig):
        self.config = config
        self.model = _load_openwakeword_model(config.model_paths)
        self.last_trigger = 0.0

    def _target_keywords(self, predictions: dict[str, float]) -> Iterable[str]:
        if not predictions:
            return []
        normalized_target = _normalize_keyword(self.config.wake_word)
        normalized_keys = {_normalize_keyword(k): k for k in predictions.keys()}
        if normalized_target in normalized_keys:
            return [normalized_keys[normalized_target]]
        return predictions.keys()

    def detect(self, pcm_frame) -> bool:
        """Return True if wake word detected for the current frame."""
        predictions = self.model.predict(pcm_frame)
        if not isinstance(predictions, dict):
            return False

        now = time.time()
        if now - self.last_trigger < self.config.cooldown_s:
            return False

        for key in self._target_keywords(predictions):
            score = predictions.get(key, 0.0)
            if score >= self.config.threshold:
                logger.info(f"Wake word detected ({key} score={score:.3f})")
                self.last_trigger = now
                return True
        return False
