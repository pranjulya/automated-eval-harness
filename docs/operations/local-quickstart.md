# Local Run Quickstart

Status: **NOT YET RUN LOCALLY** (noted 2026-09-10). This file captures exactly
what to run when you pick this up. Nothing here needs the network, credentials,
or a paid provider.

## Prerequisites
- Python 3.12+ (your system `python3` is 3.9; `uv` fetches 3.12 for you).
- [`uv`](https://docs.astral.sh/uv/) installed.
- Docker only if you want the container check.

## Steps

```bash
cd /Users/pranjulyabajpai/src/genAI/automated-eval-harness

# 1. Install locked dependencies into .venv
uv sync --extra dev --frozen

# 2. Tests / lint / types (sanity check)
uv run pytest tests -q
uv run ruff check .
uv run mypy src/eval_harness

# 3. Validate the golden suite
uv run python -m eval_harness validate \
  --suite evaluation/datasets/golden-v1 \
  --config evaluation/configs/validation.json

# 4. Run all 50 cases against the deterministic fake target
uv run python -m eval_harness run \
  --suite evaluation/datasets/golden-v1 \
  --config evaluation/configs/fake.json
# note the RUN_ID it prints

# 5. Inspect and replay
uv run python -m eval_harness inspect --run <RUN_ID> --failures-only
uv run python -m eval_harness replay  --run <RUN_ID>

# 6. Promote a baseline, then compare a second run
cat > /tmp/approval.json <<'EOF'
{"actor": "me", "approval_evidence": ["local-review"], "reason": "first baseline"}
EOF
uv run python -m eval_harness promote-baseline --run <RUN_ID> \
  --suite golden-v1 --channel stable --reason "first baseline" \
  --approval-file /tmp/approval.json

uv run python -m eval_harness run --suite evaluation/datasets/golden-v1 \
  --config evaluation/configs/fake.json --run-id candidate
uv run python -m eval_harness compare --candidate candidate \
  --baseline stable --suite golden-v1
```

## Where things go
- Runs: `./artifacts/runs/<run-id>/` (override with `EVAL_HARNESS_ARTIFACT_ROOT=/path`).
- Baselines: `./artifacts/baselines/<suite>/<channel>.json` (immutable history alongside).
- Config: `EVAL_HARNESS_ENVIRONMENT`, `EVAL_HARNESS_LOG_LEVEL`,
  `EVAL_HARNESS_ARTIFACT_ROOT`, `EVAL_HARNESS_SECRET_REFS` (names only).

## Container
```bash
docker build -t eval-harness .
docker run --rm eval-harness --version
```
Requires Docker Desktop running (it was unresponsive on this machine earlier).

## Known limitation before you try it
- **The HTTP API is not runnable locally yet.** `src/eval_harness/api.py` exposes
  `create_app(...)` and is covered by `tests/unit/test_api.py` via FastAPI's
  `TestClient`, but there is **no ASGI server dependency (`uvicorn`) and no
  `eval-harness serve` command** to construct services and boot it. Add those to
  exercise the API with `curl` locally (tracked as a Phase 08 follow-up).
- Semantic judge scoring returns `REVIEW_REQUIRED` by design (Phase 05 is
  `DEFERRED_POST_V1`); the default `golden-v1` cases are all deterministic.
