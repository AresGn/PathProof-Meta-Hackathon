"""Voice transcription call; the only place that knows the model parameters for it."""
import json
import shutil
import subprocess
from pathlib import Path

import httpx
import imageio_ffmpeg

# https://dev.meta.ai/docs/api-reference/voice/transcribe and .../voice/schemas
VOICE_MODEL = "muse-voice-transcribe-1.0"
TRANSCRIBE_PATH = "asr/transcribe"
SAMPLE_RATE = 24000  # engine-native rate, https://dev.meta.ai/docs/speech-to-text
LANGUAGE_BIAS = ["French"]  # free-text language names, .../voice/schemas
# Recognition biasing, same page: the terms the agent cannot afford to mishear
# (both supported series, E1.1, plus SVT; no city: it could be heard wrongly).
KEYWORDS = ["série C", "série D", "SVT"]
TIMEOUT_SECONDS = 120
CONVERT_TIMEOUT_SECONDS = 120  # safety net: converting 32 MB at most takes seconds


def find_ffmpeg() -> str:
    """System ffmpeg first; the pip-bundled binary where none is installed (Vercel, E5.4)."""
    return shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()


def convert_to_wav(source: Path, target: Path) -> None:
    """Convert any audio ffmpeg reads to the WAV the endpoint requires.

    Mono 16-bit PCM at 24 kHz (the API rejects anything else with a 400,
    docs/decisions.md E0.5). Command from https://dev.meta.ai/docs/speech-to-text.
    """
    subprocess.run([find_ffmpeg(), "-y", "-v", "error", "-i", str(source), "-ac", "1",
                    "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-map_metadata", "-1",
                    str(target)], check=True, timeout=CONVERT_TIMEOUT_SECONDS)


def request_transcript(client, wav_path: Path, keywords: list[str] | None = None):
    """POST the WAV to the transcribe endpoint; return the raw HTTP response."""
    request = {"model": VOICE_MODEL, "audioEncoding": "WAV", "languageBias": LANGUAGE_BIAS,
               "keywords": keywords if keywords is not None else KEYWORDS}
    return httpx.post(
        f"{client.base_url}{TRANSCRIBE_PATH}",
        headers={"Authorization": f"Bearer {client.api_key}", "Accept": "application/json"},
        files={"request": (None, json.dumps(request), "application/json"),
               "audio": (wav_path.name, wav_path.read_bytes(), "audio/wav")},
        timeout=TIMEOUT_SECONDS,
    )
