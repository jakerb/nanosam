"""OpenAI audio client for transcription and TTS."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from loguru import logger


class OpenAIAudioClient:
    """Minimal OpenAI audio client (transcribe + TTS)."""

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openai.com/v1",
        transcribe_model: str = "gpt-4o-mini-transcribe",
        tts_model: str = "gpt-4o-mini-tts",
        tts_voice: str = "alloy",
        tts_speed: float = 1.0,
        tts_format: str = "wav",
    ) -> None:
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.transcribe_model = transcribe_model
        self.tts_model = tts_model
        self.tts_voice = tts_voice
        self.tts_speed = tts_speed
        self.tts_format = tts_format

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
        }

    async def transcribe(
        self,
        file_path: str | Path,
        language: str | None = None,
    ) -> str:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Audio file not found: {file_path}")
            return ""

        data: dict[str, Any] = {
            "model": self.transcribe_model,
            "response_format": "json",
        }
        if language:
            data["language"] = language

        try:
            async with httpx.AsyncClient() as client:
                with open(path, "rb") as f:
                    files = {"file": (path.name, f)}
                    response = await client.post(
                        f"{self.api_base}/audio/transcriptions",
                        headers=self._headers(),
                        data=data,
                        files=files,
                        timeout=60.0,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    return str(payload.get("text", "")).strip()
        except Exception as e:
            logger.error(f"OpenAI transcription error: {e}")
            return ""

    async def speak(self, text: str, output_path: str | Path) -> Path | None:
        path = Path(output_path)
        payload: dict[str, Any] = {
            "model": self.tts_model,
            "voice": self.tts_voice,
            "input": text,
            "response_format": self.tts_format,
            "speed": self.tts_speed,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/audio/speech",
                    headers=self._headers(),
                    json=payload,
                    timeout=60.0,
                )
                response.raise_for_status()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(response.content)
                return path
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            return None
