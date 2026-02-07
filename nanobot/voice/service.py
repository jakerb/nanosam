"""Background voice assistant service with wake word detection."""

from __future__ import annotations

import asyncio
import queue
import time
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.agent.loop import AgentLoop
from nanobot.config.schema import Config
from nanobot.utils.helpers import get_data_path
from nanobot.voice.openai_audio import OpenAIAudioClient
from nanobot.voice.wakeword import WakeWordConfig, WakeWordDetector, WakeWordDependencyError


class VoiceDependencyError(RuntimeError):
    """Raised when required voice dependencies are missing."""


@dataclass
class VoiceRuntimeConfig:
    sample_rate: int
    chunk_ms: int
    pre_roll_ms: int
    max_record_seconds: float
    min_record_seconds: float
    silence_threshold: float
    silence_ms: int
    input_device: str | None
    output_device: str | None


class VoiceAssistantService:
    """Always-on voice assistant with wake word detection."""

    def __init__(self, config: Config, agent: AgentLoop):
        self.config = config
        self.agent = agent
        self._running = False
        self._speaking = False
        self._loop: asyncio.AbstractEventLoop | None = None

        voice_cfg = config.voice
        self.wake_config = WakeWordConfig(
            wake_word=voice_cfg.wake_word,
            model_paths=voice_cfg.wakeword_models or None,
            threshold=voice_cfg.wakeword_threshold,
            cooldown_s=voice_cfg.wakeword_cooldown_s,
        )
        self.runtime_config = VoiceRuntimeConfig(
            sample_rate=voice_cfg.sample_rate,
            chunk_ms=voice_cfg.chunk_ms,
            pre_roll_ms=voice_cfg.pre_roll_ms,
            max_record_seconds=voice_cfg.max_record_seconds,
            min_record_seconds=voice_cfg.min_record_seconds,
            silence_threshold=voice_cfg.silence_threshold,
            silence_ms=voice_cfg.silence_ms,
            input_device=voice_cfg.input_device or None,
            output_device=voice_cfg.output_device or None,
        )

        import os
        api_key = (
            voice_cfg.openai_api_key
            or config.providers.openai.api_key
            or os.environ.get("OPENAI_API_KEY")
        )
        if not api_key:
            raise VoiceDependencyError(
                "OpenAI API key missing. Set voice.openaiApiKey or providers.openai.apiKey."
            )

        self.audio_client = OpenAIAudioClient(
            api_key=api_key,
            api_base=voice_cfg.openai_api_base,
            transcribe_model=voice_cfg.openai_transcribe_model,
            tts_model=voice_cfg.openai_tts_model,
            tts_voice=voice_cfg.openai_tts_voice,
            tts_speed=voice_cfg.openai_tts_speed,
            tts_format=voice_cfg.openai_tts_format,
        )

        self.data_dir = get_data_path() / "voice"

        self._sd = None
        self._np = None

    async def start(self) -> None:
        """Start the voice assistant service (runs until stopped)."""
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_running_loop()
        logger.info("Voice assistant started")
        try:
            await asyncio.to_thread(self._run_blocking)
        finally:
            self._running = False
            logger.info("Voice assistant stopped")

    def stop(self) -> None:
        """Stop the voice assistant service."""
        self._running = False

    def _import_deps(self) -> None:
        try:
            import numpy as np  # type: ignore
            import sounddevice as sd  # type: ignore
        except Exception as e:  # pragma: no cover - import error path
            raise VoiceDependencyError(
                "Audio dependencies missing. Install with: pip install 'nanobot-ai[voice]'"
            ) from e
        self._np = np
        self._sd = sd

    def _run_blocking(self) -> None:
        self._import_deps()

        try:
            detector = WakeWordDetector(self.wake_config)
        except WakeWordDependencyError as e:
            logger.error(str(e))
            return

        cfg = self.runtime_config
        frame_samples = int(cfg.sample_rate * cfg.chunk_ms / 1000)
        if frame_samples <= 0:
            logger.error("Invalid chunk_ms/sample_rate configuration")
            return

        q: queue.Queue[Any] = queue.Queue()
        pre_roll_frames = max(1, int(cfg.pre_roll_ms / cfg.chunk_ms))
        ring = deque(maxlen=pre_roll_frames)

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio input status: {status}")
            mono = indata[:, 0].copy()
            q.put(mono)

        stream_kwargs: dict[str, Any] = {
            "samplerate": cfg.sample_rate,
            "channels": 1,
            "dtype": "int16",
            "blocksize": frame_samples,
            "callback": callback,
        }
        if cfg.input_device:
            stream_kwargs["device"] = cfg.input_device

        try:
            with self._sd.InputStream(**stream_kwargs):
                logger.info("Listening for wake word...")
                while self._running:
                    try:
                        frame = q.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    if self._speaking:
                        continue

                    ring.append(frame)
                    if detector.detect(frame):
                        utterance = list(ring)
                        utterance.extend(self._record_utterance(q))
                        audio_path = self._write_wav(utterance, cfg.sample_rate)
                        if audio_path and self._loop:
                            future = asyncio.run_coroutine_threadsafe(
                                self._handle_utterance(audio_path),
                                self._loop,
                            )
                            try:
                                future.result()
                            except Exception as e:
                                logger.error(f"Voice handler error: {e}")
        except Exception as e:
            logger.error(f"Audio stream error: {e}")

    def _record_utterance(self, q: queue.Queue[Any]):
        cfg = self.runtime_config
        max_frames = max(1, int(cfg.max_record_seconds * 1000 / cfg.chunk_ms))
        min_frames = max(1, int(cfg.min_record_seconds * 1000 / cfg.chunk_ms))
        silence_limit = max(1, int(cfg.silence_ms / cfg.chunk_ms))

        frames = []
        silence_frames = 0

        for _ in range(max_frames):
            try:
                frame = q.get(timeout=1.0)
            except queue.Empty:
                break
            frames.append(frame)
            rms = self._rms(frame)
            if rms < cfg.silence_threshold:
                silence_frames += 1
            else:
                silence_frames = 0
            if len(frames) >= min_frames and silence_frames >= silence_limit:
                break
        return frames

    def _rms(self, frame) -> float:
        np = self._np
        if np is None:
            return 0.0
        samples = frame.astype(np.float32)
        return float(np.sqrt(np.mean(samples * samples)))

    def _write_wav(self, frames, sample_rate: int) -> Path | None:
        if not frames:
            return None
        self.data_dir.mkdir(parents=True, exist_ok=True)
        filename = f"utterance_{int(time.time() * 1000)}.wav"
        path = self.data_dir / filename
        try:
            with wave.open(str(path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                for frame in frames:
                    wf.writeframes(frame.tobytes())
            return path
        except Exception as e:
            logger.error(f"Failed to write audio file: {e}")
            return None

    async def _handle_utterance(self, audio_path: Path) -> None:
        text = await self.audio_client.transcribe(
            audio_path,
            language=self.config.voice.language or None,
        )
        if not text:
            logger.info("No transcription result")
            return

        logger.info(f"Transcribed: {text}")
        response = await self.agent.process_direct(
            text,
            session_key="voice:local",
            channel="voice",
            chat_id="local",
        )

        if not response:
            return

        self._speaking = True
        try:
            tts_path = await self.audio_client.speak(
                response,
                self.data_dir / "response.wav",
            )
            if tts_path:
                await asyncio.to_thread(self._play_wav, tts_path)
        finally:
            self._speaking = False

    def _play_wav(self, path: Path) -> None:
        if self._sd is None or self._np is None:
            return
        try:
            with wave.open(str(path), "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                data = self._np.frombuffer(frames, dtype=self._np.int16)
                data = data.reshape(-1, wf.getnchannels())
                self._sd.play(data, wf.getframerate(), device=self.runtime_config.output_device)
                self._sd.wait()
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
