---
name: voice-assistant
description: Run the local wake-word voice assistant ("hey jarvis") with OpenAI voice + TTS.
homepage: https://github.com/HKUDS/nanobot
metadata: {"nanobot":{"emoji":"🎙️"}}
---

# Voice Assistant (Wake Word)

This skill enables a local, always-on voice assistant for nanobot with the wake word **"hey jarvis"**. It runs on-device for wake word detection and uses OpenAI audio models for transcription + TTS.

## Install (Raspberry Pi 4)

```bash
# System deps for audio I/O
sudo apt-get update
sudo apt-get install -y portaudio19-dev libsndfile1

# Python deps
pip install 'nanobot-ai[voice]'
```

## Configure

Edit `~/.nanobot/config.json` and enable voice:

```json
{
  "voice": {
    "enabled": true,
    "wakeWord": "hey jarvis",
    "openaiTtsVoice": "alloy"
  }
}
```

Notes:
- "hey jarvis" is included as a built-in openwakeword model. You only need `wakewordModels` for a custom wake phrase.
- Set `voice.openaiApiKey` or `providers.openai.apiKey` in config.
- Default sample rate is 16kHz for Raspberry Pi 4 efficiency.

## Run

```bash
# Run standalone voice assistant
nanobot voice

# Or run with the full gateway (channels + voice)
nanobot gateway
```

## Tips

- If the wake word is too sensitive, raise `voice.wakewordThreshold` (0.5 → 0.7).
- If recordings cut off, increase `voice.preRollMs` or `voice.silenceMs`.
- Use `voice.inputDevice` and `voice.outputDevice` if you have multiple audio devices.
