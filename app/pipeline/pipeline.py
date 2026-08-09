import os
import tempfile

from app.pipeline.chunking import needs_chunking, transcribe_chunked
from app.pipeline.normalize import normalize_audio, probe_audio
from app.pipeline.transcribe import transcribe_audio


def run_pipeline(input_path: str) -> dict:
    """Single entry point: validate -> normalize -> transcribe (chunked only if long).

    Used identically by the synchronous /v1/transcribe route and the async RQ job
    task, so there is exactly one implementation of the logic that matters. Raises
    UnsupportedAudioError (permanent, caller should not retry) if the file can't be
    identified or normalized as audio.
    """
    info = probe_audio(input_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        normalized_path = os.path.join(tmp_dir, "normalized.wav")
        normalize_audio(input_path, normalized_path)

        if needs_chunking(info["duration_seconds"]):
            result = transcribe_chunked(normalized_path)
        else:
            result = transcribe_audio(normalized_path)

    result["duration_seconds"] = info["duration_seconds"]
    return result
