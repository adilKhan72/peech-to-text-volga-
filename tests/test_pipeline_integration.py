import os

import pytest

from app.pipeline.pipeline import run_pipeline

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.mark.slow
def test_run_pipeline_transcribes_real_speech_end_to_end():
    result = run_pipeline(os.path.join(FIXTURES, "speech_sample.wav"))

    transcript = result["text"].lower()
    assert "brown fox" in transcript
    assert "lazy dog" in transcript
    assert len(result["segments"]) >= 1
    assert result["segments"][0]["start"] == 0.0
