# Local Run Quickstart

Status: **verified end-to-end on 2026-11-03** (Linux, Python 3.13 via `uv`).
Nothing here needs the network after `uv sync`, credentials, or a paid provider.

## Prerequisites
- [`uv`](https://docs.astral.sh/uv/) installed. It fetches Python 3.12+ if your
  system Python is older.
- Docker only if you want the container check.

## 1. Install and sanity-check

```bash
cd automated-eval-harness
uv sync --extra dev --frozen
uv run pytest tests -q
uv run ruff check .
uv run mypy src/eval_harness
```

## 2. Validate the golden suite

```bash
uv run eval-harness validate \
  --suite evaluation/datasets/golden-v1 --config evaluation/configs/validation.json
# OK golden-v1 1.0.1 cases=50 hash=...
```

## 3. Run, inspect, replay

```bash
uv run eval-harness run --suite evaluation/datasets/golden-v1 \
  --config evaluation/configs/fake.json --run-id clean
uv run eval-harness inspect --run clean --failures-only
uv run eval-harness replay  --run clean
```

The Markdown report is at `artifacts/runs/clean/report.md`.

## 4. Promote a baseline

```bash
cat > approval.json <<'EOF'
{"actor": "me", "approval_evidence": ["local-review"], "reason": "first baseline"}
EOF
uv run eval-harness promote-baseline --run clean --suite golden-v1 \
  --channel stable --reason "first baseline" --approval-file approval.json
```

## 5. Gate a good candidate (PASS, exit 0)

```bash
uv run eval-harness run --suite evaluation/datasets/golden-v1 \
  --config evaluation/configs/fake.json --run-id candidate
uv run eval-harness compare --candidate candidate --baseline stable --suite golden-v1
# decision=PASS
```

## 6. Gate a regressed candidate (BLOCK, exit 2)

`evaluation/configs/fake-regressed.json` points at a fake target with three
deliberate defects: a wrong factual answer (`text-001`), a schema-breaking
structured output (`struct-001`), and a forbidden tool call (`tool-001`).

```bash
uv run eval-harness run --suite evaluation/datasets/golden-v1 \
  --config evaluation/configs/fake-regressed.json --run-id regressed
uv run eval-harness inspect --run regressed --failures-only
uv run eval-harness compare --candidate regressed --baseline stable --suite golden-v1
echo "exit=$?"
# decision=BLOCK reasons=HARD_INVARIANT_SCHEMA,HARD_INVARIANT_FORBIDDEN_TOOL,... exit=2
```

The pass rate is still 94%. The gate blocks because hard invariants never
average away.

## 7. HTTP API

```bash
export EVAL_HARNESS_JWT_SECRET=replace-with-a-long-random-local-secret
uv run eval-harness serve --config evaluation/configs/fake.json --port 8080
```

In a second terminal (same `EVAL_HARNESS_JWT_SECRET`):

```bash
TOKEN=$(uv run eval-harness dev-token --actor ci --role runner --role reader)
curl -s localhost:8080/health/ready
curl -s -X POST localhost:8080/v1/runs -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: demo-1" -H 'Content-Type: application/json' \
  -d '{"suite_path":"evaluation/datasets/golden-v1","run_id":"api-run-1"}'
curl -s -X POST localhost:8080/v1/comparisons -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"candidate_run_id":"api-run-1","suite":"golden-v1","channel":"stable"}'
```

Swagger UI: <http://127.0.0.1:8080/docs>. A `reader`-only token gets `403` on
`POST /v1/runs`.

## Where things go
- Runs: `./artifacts/runs/<run-id>/` (override with `EVAL_HARNESS_ARTIFACT_ROOT=/path`).
- Baselines: `./artifacts/baselines/<suite>/<channel>.json`.
- Run IDs are immutable: to repeat the walkthrough, delete `./artifacts` or use new `--run-id` values.

## Container
```bash
docker build -t eval-harness .
docker run --rm eval-harness --version
```

## Known limitations
- Semantic judge scoring returns `REVIEW_REQUIRED` by design (Phase 05 is
  `DEFERRED_POST_V1`); the default `golden-v1` cases are all deterministic.
- API idempotency records and online samples are in memory and reset on restart.
