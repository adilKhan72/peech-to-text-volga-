import os
import wave

import pytest

from app.pipeline.exceptions import UnsupportedAudioError
from app.pipeline.normalize import normalize_audio, probe_audio

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.mark.parametrize("filename", ["tone_stereo_44k.wav", "tone_mono.mp3"])
def test_probe_identifies_real_audio_regardless_of_container(filename):
    info = probe_audio(os.path.join(FIXTURES, filename))

    assert info["duration_seconds"] > 1.5
    assert info["channels"] in (1, 2)


def test_probe_rejects_file_that_is_not_actually_audio():
    with pytest.raises(UnsupportedAudioError):
        probe_audio(os.path.join(FIXTURES, "not_audio.wav"))


@pytest.mark.parametrize("filename", ["tone_stereo_44k.wav", "tone_mono.mp3"])
def test_normalize_produces_16khz_mono_pcm_regardless_of_input_format(tmp_path, filename):
    output_path = str(tmp_path / "normalized.wav")

    normalize_audio(os.path.join(FIXTURES, filename), output_path)

    with wave.open(output_path, "rb") as wav_file:
        assert wav_file.getframerate() == 16000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2  # 16-bit


def test_normalize_raises_on_unsupported_input(tmp_path):
    output_path = str(tmp_path / "normalized.wav")

    with pytest.raises(UnsupportedAudioError):
        normalize_audio(os.path.join(FIXTURES, "not_audio.wav"), output_path)
