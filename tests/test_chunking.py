from app.pipeline.chunking import needs_chunking, offset_segments


def test_offset_segments_shifts_start_and_end():
    local_segments = [
        {"start": 0.0, "end": 2.5, "text": "hello"},
        {"start": 2.5, "end": 5.0, "text": "world"},
    ]

    shifted = offset_segments(local_segments, offset_seconds=120.0)

    assert shifted == [
        {"start": 120.0, "end": 122.5, "text": "hello"},
        {"start": 122.5, "end": 125.0, "text": "world"},
    ]


def test_offset_segments_does_not_mutate_input():
    local_segments = [{"start": 0.0, "end": 1.0, "text": "hi"}]

    offset_segments(local_segments, offset_seconds=10.0)

    assert local_segments == [{"start": 0.0, "end": 1.0, "text": "hi"}]


def test_offset_segments_with_zero_offset_is_identity():
    local_segments = [{"start": 3.1, "end": 4.2, "text": "hey"}]

    assert offset_segments(local_segments, offset_seconds=0.0) == local_segments


def test_needs_chunking_below_threshold_is_false():
    assert needs_chunking(duration_seconds=30.0) is False


def test_needs_chunking_above_threshold_is_true():
    assert needs_chunking(duration_seconds=99999.0) is True
