# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
