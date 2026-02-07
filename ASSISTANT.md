# Voice Assistant ("hey jarvis")

This project now includes a local wake-word voice assistant that runs in the background on a Raspberry Pi 4. It uses on-device wake word detection and OpenAI audio models for transcription + text-to-speech (TTS), then routes text into nanobot.

## Quick Start (Raspberry Pi 4)

1. Install system deps:

```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev libsndfile1
```

2. Install Python deps:

```bash
pip install 'nanobot-ai[voice]'
```

3. Enable voice in config (`~/.nanobot/config.json`):

```json
{
  "voice": {
    "enabled": true,
    "wakeWord": "hey jarvis",
    "openaiTtsVoice": "alloy"
  }
}
```

4. Run:

```bash
# Voice-only
nanobot voice

# Or full gateway (channels + voice)
nanobot gateway
```

## Wake Word Model ("hey jarvis")

The wake word detector is powered by `openwakeword`. The phrase "hey jarvis" is available as a built-in model, so no custom `.onnx` is required unless you want a different wake word.

## How It Works

1. Always-on microphone stream at 16 kHz.
2. Local wake word detection (openwakeword).
3. Record short utterance after trigger.
4. OpenAI transcription (`gpt-4o-mini-transcribe`).
5. nanobot agent responds.
6. OpenAI TTS (`gpt-4o-mini-tts`) plays audio back.

## Config Reference

`voice.enabled`
Enable the background voice assistant.

`voice.wakeWord`
Wake phrase (default: `"hey jarvis"`).

`voice.wakewordModels`
List of paths to openwakeword `.onnx` models.

`voice.wakewordThreshold`
Detection threshold (0.5 default). Raise if too sensitive.

`voice.sampleRate`
Audio input rate (default 16000).

`voice.chunkMs`
Frame size in milliseconds (default 80).

`voice.preRollMs`
Pre-roll audio buffer (default 500 ms).

`voice.maxRecordSeconds`
Maximum utterance duration (default 8 seconds).

`voice.minRecordSeconds`
Minimum utterance duration (default 2 seconds).

`voice.silenceThreshold`
RMS energy threshold for silence detection.

`voice.silenceMs`
Silence duration to end recording.

`voice.inputDevice`
Optional input device name or index.

`voice.outputDevice`
Optional output device name or index.

`voice.openaiApiKey`
OpenAI API key override (otherwise uses `providers.openai.apiKey`).

`voice.openaiTranscribeModel`
Default `gpt-4o-mini-transcribe`.

`voice.openaiTtsModel`
Default `gpt-4o-mini-tts`.

`voice.openaiTtsVoice`
TTS voice name (e.g., `alloy`, `ash`, `nova`).

`voice.openaiTtsSpeed`
Playback speed (default 1.0).

`voice.openaiTtsFormat`
Audio format (default `wav`).

## Raspberry Pi 4 Notes

- Keep `sampleRate=16000` and `chunkMs=80` for CPU headroom.
- Use a USB mic with hardware gain if wake word detection is inconsistent.
- If audio playback is choppy, try setting `voice.outputDevice` explicitly.

## Troubleshooting

- **No wake word detection**: confirm your `.onnx` model path and raise `wakewordThreshold` gradually.
- **No transcription**: verify OpenAI API key and internet connectivity.
- **No audio playback**: check `aplay -l` and set `voice.outputDevice`.
