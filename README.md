# Speech-to-Text Pipeline

A transcription service: upload audio, get text back with per-segment timestamps.
Deliberately scoped as a focused project, not dressed up as something bigger than
it is.

## What's here

```
validate → normalize (ffmpeg) → transcribe (faster-whisper) → segments + timestamps
```

Two ways to hit that pipeline:

- **`POST /v1/transcribe`** — synchronous. Upload a file, get the transcript back
  in the same response. For short clips and quick demos.
- **`POST /v1/jobs`** + **`GET /v1/jobs/{id}`** — asynchronous. Upload a file, get a
  job id back immediately, poll for the result. This is the real path for anything
  long, and the one that actually exercises the concurrency/retry/queue design.

## Running it locally (no Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit API_KEY if you want something other than the default

# needs ffmpeg + a redis-server reachable at REDIS_URL — on Debian/Ubuntu:
#   sudo apt install ffmpeg redis-server

# three processes:
redis-server &
python worker.py &
uvicorn app.main:app --reload
```

First real transcription downloads the model from the Hugging Face Hub (needs
internet once; cached under `~/.cache/huggingface` after that) — you'll see an
"unauthenticated requests to the HF Hub" warning on that first run, which is
expected and harmless.

```bash
curl -X POST http://localhost:8000/v1/transcribe \
  -H "X-API-Key: <your API_KEY>" \
  -F "file=@sample.wav"

curl -X POST http://localhost:8000/v1/jobs \
  -H "X-API-Key: <your API_KEY>" \
  -F "file=@sample.wav"
# => {"job_id": "...", "status": "queued"}

curl http://localhost:8000/v1/jobs/<job_id> -H "X-API-Key: <your API_KEY>"
```

## Using it from a browser

There's no custom frontend here — this is a backend-focused project. But FastAPI
auto-generates an interactive docs page for every route, so files and responses can
be tried directly, no extra code needed.

1. Start the app (see above).
2. Open `http://localhost:8000/docs`.
3. Expand `POST /v1/transcribe` (or `/v1/jobs`) and click **"Try it out"**.
4. Fill in `X-API-Key`, pick a file, click **"Execute"**.
5. For the async path: copy the `job_id` from the response, expand
   `GET /v1/jobs/{job_id}`, paste it in, and Execute again to check the result.

`http://localhost:8000/redoc` has a read-only version of the same reference.

## Running it via Docker

```bash
docker compose up --build
```

Brings up `redis`, `api`, and `worker` together, sharing a volume for audio so the
worker can read what the api container saved — separate containers means separate
filesystems, and without that shared volume the worker would 404 on every file.

## Testing

```bash
pytest          # fast, mocked/pure-logic tests only
pytest -m slow  # real end-to-end: loads the actual faster-whisper model
```

`tests/fixtures/` has a few tiny generated audio files (different containers/codecs),
a deliberately corrupted one, and a synthesized (`espeak-ng`) speech clip with known
text, so the slow test can check actual words, not just "didn't crash."

## Design decisions

**Normalize once, don't branch per format.** Every upload gets decoded and
re-encoded to one fixed target (16kHz mono 16-bit PCM WAV) via `ffmpeg` before
anything else touches it. `ffprobe` identifies the real container/codec first —
never trust the extension. One input shape downstream means one code path to test,
not one per format.

**faster-whisper over a managed API.** No per-minute cost, runs fully offline, and
this machine has no GPU so CPU + int8 quantization was the right fit. A managed API
(AWS Transcribe, Deepgram, etc.) makes more sense at higher volume, or if
diarization/PII-redaction is needed without building it — trading a per-minute bill
and a network dependency for zero ops.

**Chunking is conditional, not universal.** faster-whisper already slides through
long audio internally (~30s windows, its own bundled Silero VAD) and returns
correctly timestamped segments — under `LONG_AUDIO_THRESHOLD_SECONDS` (10 min
default), calling it directly is simplest and just as correct. Above that,
`chunking.py` splits audio into VAD-aligned chunks, transcribes each independently,
and stitches timestamps back by adding each chunk's offset to its local segment
times. The goal is bounding memory and enabling parallelism on long files, not
working around a context limit that doesn't exist for typical ones.

**Permanent vs. transient failures, not "retry N times."** `UnsupportedAudioError`
(bad/corrupt file) is permanent — the job fails immediately and never retries, since
retrying a file that will never decode just burns compute. Everything else is
transient and left to propagate so RQ's `Retry` (3 attempts, 10s/30s/90s backoff)
schedules another attempt. RQ's `on_failure` callback fires on every failed attempt,
not just the last, so the task checks `job.retries_left` itself before writing
`status=failed`.

**Redis + RQ over `BackgroundTasks`.** A real worker pool, not an in-process
callback — worker count is the actual concurrency throttle, jobs survive an API
restart, and retry/backoff comes built in. The same Redis instance also backs the
rate limiter, so no second piece of infrastructure is needed.

**Storage is one interface, one implementation (`app/storage/`).** Audio is
addressed by a `storage_key` everywhere — nothing outside `local_fs.py` knows it's a
path on disk, so swapping in S3 later is a one-file change. The transcript is small
and structured, so it lives directly on the `Job` row instead of a second file
store.

**A static API key, not real auth; SQLite, not Postgres.** Both are intentional
simplifications for this project's scope — `app/auth.py` and `app/config.py` say
so. Production would put OAuth2/JWT in front of this, and Postgres behind it once
more than one process needs to write concurrently.

**Not handled, on purpose:** speaker diarization is a distinct model/step, out of
scope here. Same for language hints beyond Whisper's own auto-detection.

## Known limitations

- **Long-audio chunking** has only been unit-tested against synthetic segment data,
  never against a real file over the 10-minute threshold.
- **Rate limiting** has never actually been pushed past its configured limit.
- **The sync endpoint's concurrency semaphore** has only been hit one request at a
  time, not under real concurrent load.

These would be the first three things to properly test given more time.

## Project layout

```
app/
  main.py                # FastAPI app + lifespan (creates DB tables on startup)
  config.py               # Settings, from .env
  auth.py                  # API key dependency
  rate_limit.py             # slowapi limiter (Redis-backed)
  routers/
    transcribe.py            # POST /v1/transcribe (sync)
    jobs.py                   # POST /v1/jobs, GET /v1/jobs/{id} (async)
  pipeline/
    exceptions.py             # UnsupportedAudioError (permanent) vs TransientPipelineError
    normalize.py               # ffprobe validation + ffmpeg -> 16kHz mono wav
    transcribe.py                # loads faster-whisper once; simple full-file path
    chunking.py                   # VAD-aligned splitting + timestamp stitching for long audio
    pipeline.py                    # single entry point: validate -> normalize -> transcribe
  storage/
    base.py                        # AudioStorage interface
    local_fs.py                     # local-filesystem implementation
  jobs/
    queue.py                        # RQ queue + Retry config
    tasks.py                         # the function an rq worker actually runs
  db/
    models.py                        # Job (status, storage_key, transcript, error, attempts)
    session.py                        # SQLite engine/session
worker.py                                # rq worker entrypoint
tests/                                    # pytest (fast, default) + one @pytest.mark.slow
Dockerfile, docker-compose.yml             # portability; not the primary local run mode
```
