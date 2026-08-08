# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-08-08

### Added
- **Auto-converter** (`auto_convert.py`):
  - Continuously converts normal documents day-by-day (plan.json `days_normal`)
  - Skips already-converted blocks (resume support) and records progress
  - Checkpoint every 10 blocks for human quality review
  - Writes complex documents to `_mineru_tools/complex_list.md` for later
    cloud-API conversion
- **Serial-stability config**: on ≤16 GB RAM machines, hybrid mode forked
  multiple worker processes and exhausted memory. Fixed by forcing serial:
  - `MINERU_DEVICE_MODE=cpu`, `CUDA_VISIBLE_DEVICES=""` (disable GPU → torch /
    PaddleOCR won't OOM)
  - `MINERU_PROCESSING_WINDOW_SIZE=2`, `MINERU_API_MAX_CONCURRENT_REQUESTS=1`,
    `MINERU_PDF_RENDER_THREADS=1`, `OMP_NUM_THREADS=1`
  - Measured: serial hybrid converts 109 pages in ~82 min (2 pages / ~90 s),
    memory stable ~3.5 GB
- **Complex-document pre-scan**: marks PDFs as normal (has text layer) vs
  complex (scanned / dense images / formulas). Complex docs route to the
  mineru.net cloud API (1000 pages/day); normal docs use local GLM bridge.

### Changed
- `mineru_local_batch.py` and `auto_convert.py` now set the serial config
  automatically in `ensure_proxy()`.
- README (EN/ZH) documents the serial config and the normal/complex split.

### Fixed
- OOM when running hybrid mode on an 8 GB GPU / 16 GB RAM laptop (worker
  processes + local models exceeded memory).
- Background process being killed by session teardown: `auto_convert.py` and
  the GLM proxy now run as detached processes (`Start-Process`).

## [0.1.0] - 2026-08-07

### Added
- **GLM adapter proxy** (`glm_mineru_proxy.py`):
  - Bridges MinerU's OpenAI-format `/v1/chat/completions` requests to GLM API
  - Detects task type (layout / table / equation / text / image) from MinerU prompts
  - Injects per-task format instructions so GLM outputs MinerU-compatible layout
  - Rate-limiting (semaphore + min interval) to avoid GLM HTTP 429
  - ThreadingHTTPServer for concurrent MinerU worker requests
  - Direct connection (bypasses system proxy) to avoid SSL flakiness
- **Batch converter** (`mineru_local_batch.py`):
  - Auto-starts the GLM proxy and configures MinerU VLM environment
  - Hybrid mode (local layout/OCR models + GLM VLM) via `hybrid-http-client`
  - Slices >200MB PDFs with PyMuPDF
  - Resume support (skips already-converted chunks)
  - Outputs to isolated `{file}_mineru/` subfolders (no source pollution)
- **Documentation**:
  - README.md (EN) / README_zh.md (ZH)
  - CHANGELOG.md / CHANGELOG_zh.md
  - LICENSE (AGPL-3.0 dual) / COMMERCIAL.md
  - requirements.txt / .gitignore

### Verified
- 10-page PDF: full pipeline runs via `vlm-http-client` (pure GLM) and
  `hybrid-http-client` (hybrid complement) — does **not** consume the
  mineru.net daily quota, does **not** need local GPU VRAM.
- Hybrid mode quality: 10.2 KB markdown vs 3.2 KB pure-GLM; near-zero OCR
  typos, aligned TOC page numbers, complete heading hierarchy.

### Known limitations
- Hybrid mode is slow (~30-60 s/page: local CPU layout/OCR + GLM rate limit).
  Batch conversions should be chunked and run over longer windows.
- Pure-GLM mode OCR has occasional typos (generic VLM, not a dedicated OCR).
- Requires ~3 GB free system RAM for hybrid mode (local pipeline models).
