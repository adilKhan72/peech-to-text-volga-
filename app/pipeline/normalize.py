import json
import subprocess

from app.pipeline.exceptions import UnsupportedAudioError

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1


def probe_audio(input_path: str) -> dict:
    """Identify the real container/codec/duration via ffprobe. Never trust the file extension."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                input_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise UnsupportedAudioError(f"ffprobe could not run: {e}") from e

    if result.returncode != 0:
        raise UnsupportedAudioError(f"ffprobe could not identify file: {result.stderr.strip()}")

    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise UnsupportedAudioError("ffprobe returned unparseable output") from e

    audio_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if not audio_streams:
        raise UnsupportedAudioError("no audio stream found in file")

    duration = float(info.get("format", {}).get("duration", 0.0))
    return {
        "duration_seconds": duration,
        "codec": audio_streams[0].get("codec_name"),
        "sample_rate": audio_streams[0].get("sample_rate"),
        "channels": audio_streams[0].get("channels"),
    }


def normalize_audio(input_path: str, output_path: str) -> None:
    """Decode whatever came in and re-encode to one fixed target: 16kHz mono PCM WAV.

    Downstream pipeline code only ever has to reason about this one input shape.
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-ac", str(TARGET_CHANNELS),
                "-ar", str(TARGET_SAMPLE_RATE),
                "-sample_fmt", "s16",
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as e:
        raise UnsupportedAudioError("ffmpeg normalization timed out") from e

    if result.returncode != 0:
        raise UnsupportedAudioError(f"ffmpeg normalization failed: {result.stderr.strip()}")
