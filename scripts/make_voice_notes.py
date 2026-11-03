"""Generate the fictional voice notes of data/samples/ with ElevenLabs (story E0.3, issue #5).

Reads ELEVENLABS_API_KEY from .env (never printed). Each note must last 30 to 60 s;
the duration is checked with ffmpeg after generation.

The noisy note (E6.1, case noisy_voice) is real speech with street noise mixed in
and a loud burst over the series letter, placed from the ElevenLabs character
timestamps: the transcript cannot tell C from D, so the agent must ask.

Usage: python scripts/make_voice_notes.py [file_name ...]   (default: all notes)
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import imageio_ffmpeg

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT_DIR / "data" / "samples"
API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
TIMESTAMPS_URL = ("https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
                  "?output_format=mp3_44100_128")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE_ID = "cYITNPiqwVi5OklXGv3H"  # young female voice, West African French accent (ElevenLabs library)
MODEL_ID = "eleven_multilingual_v2"
# Lower stability = more natural, varied delivery; docs.elevenlabs.io voice settings
VOICE_SETTINGS = {"stability": 0.35, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True, "speed": 0.95}
MIN_SECONDS, MAX_SECONDS = 30, 60  # issue #5 acceptance criteria
BACKGROUND_NOISE_VOLUME = 0.05  # street noise under the whole note, speech stays audible
BURST_VOLUME = 1.0  # covers the series letter completely
BURST_MARGIN_SECONDS = 0.25  # around the letter, so no trace of C or D is left

# Same student as releve_serie_d.jpg: moyenne générale 11,20
VOICE_NOTES = {
    "note_vocale_coherente.mp3": (
        "Bonjour... Alors, euh, je suis en terminale, série D, D comme Daniel. Au bac, j'ai eu onze virgule deux de moyenne. "
        "Ce que j'aime le plus, c'est la biologie, les SVT... vraiment, c'est ma matière préférée. "
        "Plus tard, j'aimerais travailler dans la santé... peut-être médecin. "
        "Depuis petite, je veux soigner les gens, aider ma famille, mon quartier. "
        "Pour la ville, euh... je préfère rester à Cotonou, près de mes parents. "
        "Et, honnêtement, j'aurai besoin d'une bourse, parce que les études, ça coûte cher chez nous. "
        "Voilà... merci de m'écouter."
    ),
    # docs/prd.md section 2.1, kept word for word, with spoken fillers around it
    "note_vocale_contradictoire.mp3": (
        "Euh... oui, bonjour. Bonjour, je suis en série D, j'ai eu 14 de moyenne. "
        "Voilà... J'aime beaucoup la biologie et j'aimerais travailler dans la santé, peut-être médecin. "
        "Au lycée, ce que je préférais, c'était les travaux pratiques en SVT, avec le microscope. "
        "Je préfère rester à Cotonou, et j'aurai besoin d'une bourse. "
        "Mes parents m'ont dit de bien chercher les filières où il y a des bourses... "
        "Donc, euh, je compte sur vous pour m'aider à choisir. Merci beaucoup, hein."
    ),
}
NOISY_NOTE = "note_vocale_bruitee.mp3"
# The series letter is the single character after "série " (masked by the burst)
NOISY_TEXT = (
    "Allô... bonjour. Je vous parle depuis le marché, il y a beaucoup de bruit, excusez-moi. "
    "Je suis en terminale, série D. "
    "Euh... ce que j'aime, c'est la biologie et la chimie, j'aime comprendre comment le corps fonctionne. "
    "Plus tard, je voudrais travailler dans la santé, peut-être pharmacien ou médecin, je ne sais pas encore. "
    "Mes parents veulent que je reste près de la maison. "
    "Et il me faudra une bourse, sinon ce sera difficile. Voilà, merci."
)
SERIES_LETTER = re.compile(r"série (\w)")


def read_api_key() -> str:
    for line in (ROOT_DIR / ".env").read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "ELEVENLABS_API_KEY" and value.strip():
            return value.strip()
    raise RuntimeError("ELEVENLABS_API_KEY missing from .env")


def synthesize_speech(text: str, api_key: str) -> bytes:
    body = json.dumps({"text": text, "model_id": MODEL_ID, "voice_settings": VOICE_SETTINGS}).encode()
    request = urllib.request.Request(
        API_URL.format(voice_id=VOICE_ID), data=body, method="POST",
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def synthesize_with_timestamps(text: str, api_key: str) -> tuple[bytes, dict]:
    body = json.dumps({"text": text, "model_id": MODEL_ID, "voice_settings": VOICE_SETTINGS}).encode()
    request = urllib.request.Request(
        TIMESTAMPS_URL.format(voice_id=VOICE_ID), data=body, method="POST",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read())
    return base64.b64decode(payload["audio_base64"]), payload["alignment"]


def find_series_letter_span(text: str, alignment: dict) -> tuple[float, float]:
    match = SERIES_LETTER.search(text)
    if match is None or "".join(alignment["characters"]) != text:
        raise RuntimeError("series letter not found in the aligned text")
    index = match.start(1)
    start = alignment["character_start_times_seconds"][index] - BURST_MARGIN_SECONDS
    end = alignment["character_end_times_seconds"][index] + BURST_MARGIN_SECONDS
    return max(start, 0.0), end


def add_noise(speech: bytes, burst: tuple[float, float], path: Path) -> None:
    """Mix street-like noise under the speech and a loud burst over the burst span."""
    start, end = burst
    with tempfile.TemporaryDirectory(prefix="pathproof-noise-") as work_dir:
        clean_path = Path(work_dir) / "clean.mp3"
        clean_path.write_bytes(speech)
        noise_volume = (f"volume='if(between(t,{start:.3f},{end:.3f}),"
                        f"{BURST_VOLUME},{BACKGROUND_NOISE_VOLUME})':eval=frame")
        speech_volume = f"volume='if(between(t,{start:.3f},{end:.3f}),0,1)':eval=frame"
        graph = (f"[0:a]{speech_volume}[speech];"
                 f"anoisesrc=color=pink:sample_rate=44100,{noise_volume}[noise];"
                 "[speech][noise]amix=inputs=2:duration=first:normalize=0[out]")
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(clean_path),
                        "-filter_complex", graph, "-map", "[out]", "-b:a", "128k", str(path)],
                       check=True)


def measure_duration(path: Path) -> float:
    output = subprocess.run([FFMPEG, "-i", str(path), "-f", "null", "-"],
                            capture_output=True, text=True)
    times = re.findall(r"time=(\d+):(\d+):([\d.]+)", output.stderr)
    if not times:
        raise RuntimeError(f"could not measure the duration of {path.name}")
    hours, minutes, seconds = times[-1]
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def main() -> None:
    api_key = read_api_key()
    selected_names = sys.argv[1:] or [*VOICE_NOTES, NOISY_NOTE]
    for file_name in selected_names:
        path = SAMPLES_DIR / file_name
        if file_name == NOISY_NOTE:
            speech, alignment = synthesize_with_timestamps(NOISY_TEXT, api_key)
            add_noise(speech, find_series_letter_span(NOISY_TEXT, alignment), path)
        else:
            path.write_bytes(synthesize_speech(VOICE_NOTES[file_name], api_key))
        duration = measure_duration(path)
        status = "OK" if MIN_SECONDS <= duration <= MAX_SECONDS else "HORS 30-60 s"
        print(f"{file_name}: {duration:.1f} s, {os.path.getsize(path) / 1e6:.2f} Mo, {status}")


if __name__ == "__main__":
    main()
