import io
import json
import subprocess
import wave
from types import SimpleNamespace

import httpx
import pytest

from src.tools.transcribe_voice import MAX_AUDIO_BYTES, TranscriptionError, transcribe_voice


class FakeResponse:
    """Mimics httpx.Response; never touches the network."""

    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body if body is not None else {"transcript": "bonjour"}

    @property
    def text(self):
        return json.dumps(self._body)

    def json(self):
        return self._body


class FakePost:
    """Stands in for httpx.post and records its calls."""

    def __init__(self, response=None, error=None):
        self.response = response if response is not None else FakeResponse()
        self.error = error
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error is not None:
            raise self.error
        return self.response


def wav_bytes(channels=1, sample_width=2, frame_rate=24000, frames=2400):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(frame_rate)
        wav.writeframes(b"\x00" * frames * channels * sample_width)
    return buffer.getvalue()


@pytest.fixture
def client():
    return SimpleNamespace(base_url="https://test.invalid/v1/", api_key="fake")


@pytest.fixture
def post(monkeypatch):
    fake = FakePost()
    monkeypatch.setattr("src.clients.voice.httpx.post", fake)
    return fake


@pytest.fixture(autouse=True)
def converted(monkeypatch):
    """Fake ffmpeg conversion: every input becomes a valid 24 kHz mono WAV."""
    calls = []
    valid = wav_bytes()

    def fake_convert(source, target):
        calls.append((source, target))
        target.write_bytes(valid)

    monkeypatch.setattr("src.tools.transcribe_voice.convert_to_wav", fake_convert)
    return calls


@pytest.fixture
def wav_file(tmp_path):
    path = tmp_path / "note.wav"
    path.write_bytes(wav_bytes())
    return str(path)


def transcribe(path, client):
    return transcribe_voice(path, client=client)


def test_success_returns_heard_text_plus_normalized(wav_file, client, post):
    post.response = FakeResponse(body={"transcript": "j'ai eu quatorze de moyenne"})
    assert transcribe(wav_file, client) == {
        "text": "j'ai eu quatorze de moyenne",
        "text_normalized": "j'ai eu 14 de moyenne",
        "confidence": None,
    }


def test_present_confidence_is_returned(wav_file, client, post):
    post.response = FakeResponse(body={"transcript": "bonjour", "confidence": 0.9})
    assert transcribe(wav_file, client)["confidence"] == 0.9


def test_hyphenated_compounds_are_untouched(wav_file, client, post):
    post.response = FakeResponse(body={"transcript": "quatre-vingt-dix élèves, dix-sept en SVT"})
    assert transcribe(wav_file, client)["text_normalized"] == "quatre-vingt-dix élèves, 17 en SVT"


def test_api_error_raises_typed_error(wav_file, client, post):
    post.response = FakeResponse(status_code=400, body={"error": "bad audio"})
    with pytest.raises(TranscriptionError, match="400"):
        transcribe(wav_file, client)


def test_network_failure_raises_typed_error(wav_file, client, post):
    post.error = httpx.ConnectError("connection refused")
    with pytest.raises(TranscriptionError, match="request failed"):
        transcribe(wav_file, client)


def test_empty_transcript_is_an_error_not_a_success(wav_file, client, post):
    post.response = FakeResponse(body={"transcript": "   "})
    with pytest.raises(TranscriptionError, match="empty transcript"):
        transcribe(wav_file, client)


def test_missing_transcript_is_an_error(wav_file, client, post):
    post.response = FakeResponse(body={"audioDurationMs": 100})
    with pytest.raises(TranscriptionError, match="empty transcript"):
        transcribe(wav_file, client)


def test_request_sends_model_language_and_keywords(wav_file, client, post):
    transcribe(wav_file, client)
    _, kwargs = post.calls[0]
    assert kwargs["timeout"] > 0
    request = json.loads(kwargs["files"]["request"][1])
    assert request["model"] == "muse-voice-transcribe-1.0"
    assert request["audioEncoding"] == "WAV"
    assert request["languageBias"] == ["French"]
    assert request["keywords"] == ["série C", "série D", "SVT"]
    assert kwargs["files"]["audio"][2] == "audio/wav"


def test_ogg_is_converted_before_transcribing(tmp_path, client, post, converted):
    path = tmp_path / "note.ogg"
    path.write_bytes(b"fake ogg bytes")
    assert transcribe(str(path), client)["text"] == "bonjour"
    assert len(converted) == 1
    assert converted[0][0].suffix == ".ogg"


def test_high_sample_rate_wav_is_reconverted(tmp_path, client, post, converted):
    path = tmp_path / "note.wav"
    path.write_bytes(wav_bytes(frame_rate=44100))
    assert transcribe(str(path), client)["text"] == "bonjour"
    assert len(converted) == 1


def test_stereo_wav_is_converted_not_refused(tmp_path, client, post):
    path = tmp_path / "stereo.wav"
    path.write_bytes(wav_bytes(channels=2))
    assert transcribe(str(path), client)["text"] == "bonjour"


def test_unsupported_format_raises_before_conversion_or_call(tmp_path, client, post, converted):
    path = tmp_path / "note.txt"
    path.write_bytes(b"not audio")
    with pytest.raises(TranscriptionError, match="unsupported audio type"):
        transcribe(str(path), client)
    assert converted == []
    assert post.calls == []


def test_empty_audio_file_raises_before_conversion_or_call(tmp_path, client, post, converted):
    path = tmp_path / "empty.wav"
    path.write_bytes(b"")
    with pytest.raises(TranscriptionError, match="empty"):
        transcribe(str(path), client)
    assert converted == []
    assert post.calls == []


def test_oversize_audio_raises_before_conversion_or_call(tmp_path, client, post, converted):
    path = tmp_path / "huge.wav"
    with open(path, "wb") as handle:
        handle.seek(MAX_AUDIO_BYTES)
        handle.write(b"x")
    with pytest.raises(TranscriptionError, match="too large"):
        transcribe(str(path), client)
    assert converted == []
    assert post.calls == []


def test_missing_file_raises_typed_error(client, post, converted):
    with pytest.raises(TranscriptionError, match="not found"):
        transcribe("nope.wav", client)
    assert converted == []
    assert post.calls == []


def test_garbage_conversion_output_raises_before_any_call(wav_file, client, post, monkeypatch):
    def broken_convert(source, target):
        target.write_bytes(b"not a wav file")

    monkeypatch.setattr("src.tools.transcribe_voice.convert_to_wav", broken_convert)
    with pytest.raises(TranscriptionError, match="unreadable WAV"):
        transcribe(wav_file, client)
    assert post.calls == []


def test_conversion_failure_raises_typed_error(wav_file, client, post, monkeypatch):
    def failing_convert(source, target):
        raise subprocess.CalledProcessError(1, "ffmpeg")

    monkeypatch.setattr("src.tools.transcribe_voice.convert_to_wav", failing_convert)
    with pytest.raises(TranscriptionError, match="conversion failed"):
        transcribe(wav_file, client)
    assert post.calls == []


def test_conversion_timeout_raises_typed_error(wav_file, client, post, monkeypatch):
    def slow_convert(source, target):
        raise subprocess.TimeoutExpired("ffmpeg", 120)

    monkeypatch.setattr("src.tools.transcribe_voice.convert_to_wav", slow_convert)
    with pytest.raises(TranscriptionError, match="conversion failed"):
        transcribe(wav_file, client)
    assert post.calls == []


def test_missing_converter_raises_typed_error(wav_file, client, post, monkeypatch):
    def no_ffmpeg(source, target):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr("src.tools.transcribe_voice.convert_to_wav", no_ffmpeg)
    with pytest.raises(TranscriptionError, match="ffmpeg is not installed"):
        transcribe(wav_file, client)
    assert post.calls == []


def test_too_long_audio_raises_before_any_call(wav_file, client, post, monkeypatch):
    import src.tools.transcribe_voice as tool

    monkeypatch.setattr(tool, "MAX_DURATION_SECONDS", 0)
    with pytest.raises(TranscriptionError, match="too long"):
        transcribe(wav_file, client)
    assert post.calls == []


def test_oversize_converted_audio_raises_before_any_call(tmp_path, client, post, monkeypatch):
    import src.tools.transcribe_voice as tool

    monkeypatch.setattr(tool, "MAX_AUDIO_BYTES", 1000)
    path = tmp_path / "note.ogg"
    path.write_bytes(b"tiny")
    with pytest.raises(TranscriptionError, match="converted audio too large"):
        transcribe(str(path), client)
    assert post.calls == []


def test_convert_to_wav_falls_back_to_bundled_ffmpeg(monkeypatch, tmp_path):
    from src.clients import voice

    calls = []
    monkeypatch.setattr(voice.shutil, "which", lambda name: None)
    monkeypatch.setattr(voice.imageio_ffmpeg, "get_ffmpeg_exe", lambda: "/bundled/ffmpeg")
    monkeypatch.setattr(voice.subprocess, "run", lambda command, **kwargs: calls.append(command))
    voice.convert_to_wav(tmp_path / "in.mp3", tmp_path / "out.wav")
    assert calls[0][0] == "/bundled/ffmpeg"


def test_convert_to_wav_prefers_system_ffmpeg(monkeypatch, tmp_path):
    from src.clients import voice

    calls = []
    monkeypatch.setattr(voice.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(voice.subprocess, "run", lambda command, **kwargs: calls.append(command))
    voice.convert_to_wav(tmp_path / "in.mp3", tmp_path / "out.wav")
    assert calls[0][0] == "/usr/bin/ffmpeg"
