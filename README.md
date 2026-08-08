# MinerU-GLMBridge

Bridge MinerU's document parsing to GLM (Zhipu AI) cloud vision models — so
consumer laptops can run full MinerU parsing without an 8GB+ GPU and without
burning the mineru.net daily 1000-page quota.

## The problem it solves

| Pain point | MinerU-GLMBridge |
|---|---|
| Local `vlm-engine` needs 8GB+ GPU VRAM | ✅ Runs on any laptop (VLM lives in the cloud) |
| mineru.net cloud has only 1000 free pages/day | ✅ Uses GLM's own quota instead |
| MinerU's local OCR quality for scanned PDFs | ✅ Hybrid mode: local PaddleOCR + GLM VLM |

## Two modes

| Mode | Backend | Quality | Notes |
|---|---|---|---|
| Pure GLM | `vlm-http-client` | ★★★★ | Fastest; OCR may have typos (generic VLM) |
| **Hybrid (recommended)** | `hybrid-http-client` | ★★★★★ | Local layout/OCR models + GLM VLM fallback |

## Architecture

```
MinerU (vlm-http-client / hybrid-http-client)
  ├─ layout analysis (local PP-DocLayoutV2)
  ├─ OCR / tables / formulas (local PaddleOCR, TableMaster)   [hybrid only]
  └─ VLM fallback ──► GLM adapter proxy (this repo)
                          │  listens on 127.0.0.1:8031
                          │  detects task type, injects format instruction
                          │  rate-limits to avoid HTTP 429
                          ▼
                 GLM-4.6V cloud vision (GLM quota)
```

## Files

| File | Purpose |
|---|---|
| `glm_mineru_proxy.py` | GLM adapter: converts MinerU's OpenAI-format requests to GLM API, injects per-task format instructions, rate-limits |
| `mineru_local_batch.py` | Batch converter: auto-starts the proxy, slices PDFs, calls MinerU, writes isolated per-file folders |
| `watchdog.py` | Watchdog: writes a heartbeat file every 30 s (GLM connections, fresh outputs, process alive, converted count) so an external monitor can detect stalls/deaths |

## Installation

Follow these steps in order. Each step tells you **exactly what to download**.

### Download checklist (at a glance)

| # | Download / get | Why | Where |
|---|---|---|---|
| 1 | This repo | the code | `git clone` (below) |
| 2 | Python 3.10+ | run the scripts | python.org |
| 3 | **MinerU** (+ its models) | document-parsing engine | `pip install "mineru[all]"` |
| 4 | **GLM API key** (free) | cloud vision model | Zhipu Open Platform |
| 5 | PyMuPDF | slice >200 MB PDFs | `pip install pymupdf` |

### Step 1 — Clone this repo

```bash
git clone https://github.com/SpiralQWQ/mineru-glm-bridge.git
cd mineru-glm-bridge
```

### Step 2 — Install Python 3.10+

Download Python 3.10+ from [python.org](https://www.python.org/downloads/). Check: `python --version`.

### Step 3 — Install MinerU (the document-parsing engine)

```bash
# Create a dedicated virtual environment (recommended)
python -m venv .venv-mineru
.venv-mineru\Scripts\activate        # Windows
source .venv-mineru/bin/activate     # Linux/macOS

# Install MinerU (this downloads MinerU + its OCR/table/formula models on first run)
pip install "mineru[all]"
```

First run auto-downloads the pipeline models (~2 GB) to `models/`. If that fails,
download them explicitly:

```bash
mineru-models-download -m pipeline
```

### Step 4 — Get a free GLM API key

1. Sign up at [Zhipu AI Open Platform](https://open.bigmodel.cn/)
2. Create an API key (model `glm-4.6v-flashx` has a free tier)
3. Set it:

```bash
setx GLM_API_KEY "your_glm_api_key"    # Windows
export GLM_API_KEY="your_glm_api_key"  # Linux/macOS
```

### Step 5 — Install PyMuPDF (for the batch script)

```bash
pip install pymupdf
```

Only needed if you use `mineru_local_batch.py` (it slices >200 MB PDFs).

### Step 6 — Tell the scripts where MinerU is (optional)

The batch script looks for MinerU at `~/.venv/mineru` by default. If yours is
elsewhere, set `MGB_MINERU_ENV`:

```bash
setx MGB_MINERU_ENV "C:\path\to\your\mineru-env"    # Windows
export MGB_MINERU_ENV="/path/to/your/mineru-env"    # Linux/macOS
```

---

## Quick start

Once installed, run a conversion:

```bash
# 1. Start the GLM proxy
python glm_mineru_proxy.py

# 2. Pure GLM mode (fastest; OCR may have typos)
set MINERU_VL_SERVER=http://127.0.0.1:8031
set MINERU_VL_API_KEY=%GLM_API_KEY%
set MINERU_VL_MODEL_NAME=glm-4.6v-flashx
mineru -p doc.pdf -o out -b vlm-http-client -u http://127.0.0.1:8031

# 3. Hybrid mode (better quality: local OCR + GLM VLM)
set MINERU_LMDEPLOY_DEVICE=cpu
set MINERU_PROCESSING_WINDOW_SIZE=2
mineru -p doc.pdf -o out -b hybrid-http-client -u http://127.0.0.1:8031
```

Or use the batch converter (auto-starts the proxy, slices, resumes):

```bash
setx MGB_MINERU_ENV "C:\path\to\your\mineru-env"
python mineru_local_batch.py --limit 5
```

## Serial-stability config (critical on ≤16 GB RAM)

Hybrid mode forks multiple worker processes; on low-RAM machines it exhausts
memory. **Force serial processing** — slower but memory-stable:

```bash
set MINERU_DEVICE_MODE=cpu
set CUDA_VISIBLE_DEVICES=              # disable GPU → torch/PaddleOCR won't OOM
set MINERU_LMDEPLOY_DEVICE=cpu
set MINERU_PROCESSING_WINDOW_SIZE=2    # 2 pages per window
set MINERU_API_MAX_CONCURRENT_REQUESTS=1  # serial
set MINERU_PDF_RENDER_THREADS=1
set OMP_NUM_THREADS=1
```

> Measured: serial hybrid converts a 109-page PDF in ~82 min (2 pages / ~90 s),
> memory stays ~3.5 GB. `auto_convert.py` sets all of these automatically.

## Complex-document split (cloud vs local)

A pre-scan marks each PDF as **normal** (has text layer, few images) or
**complex** (scanned / dense images / math formulas):

| Type | Detect | Convert via |
|---|---|---|
| Normal | text layer present | local hybrid-http-client (free) |
| **Complex** | no text layer / dense images / formulas | mineru.net cloud API (1000 pages/day) |

`auto_convert.py` skips complex blocks and records them in
`_mineru_tools/complex_list.md` for later cloud conversion via
`mineru_day.py --complex`.

## Watchdog (monitor for stalls)

Long serial conversions can silently stall. Run the watchdog alongside
`auto_convert.py` — it writes a heartbeat JSON every 30 s so an external
monitor (or you) can detect a dead or stuck process:

```bash
python watchdog.py
```

Heartbeat fields (`_mineru_tools/watchdog_heartbeat.json`):

| Field | Meaning |
|---|---|
| `ts` | last heartbeat timestamp (stale if old) |
| `glm_conns` | ESTABLISHED connections to the GLM proxy (0 + no outputs = stall) |
| `fresh_outputs_10min` | `full.md` files written in the last 10 min |
| `process_alive` | whether the `auto_convert` process is running |
| `converted` | blocks completed so far |

Paths are configurable via `MGB_ROOT` / `MGB_PROXY_PORT` / `MGB_HEARTBEAT`.

## Quality comparison (measured, 10-page PDF)

| Metric | Pure GLM | Hybrid |
|---|---|---|
| Markdown size | 3.2 KB | 10.2 KB |
| OCR typos | present | almost none |
| TOC page numbers | misaligned | aligned |
| Heading hierarchy | partial | complete |

## Requirements

### Third-party tools this project integrates

MinerU-GLMBridge does **not** re-implement document parsing — it orchestrates
well-known tools. Each tool has its own license and terms:

| Tool | Role in this project | Install | License |
|---|---|---|---|
| **[MinerU](https://github.com/opendatalab/MinerU)** | Document-parsing engine: PDF → Markdown. Provides the `vlm-http-client` / `hybrid-http-client` backends this bridge connects to. | `pip install mineru[all]` (v3.x recommended) | [MinerU Open Source License](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md) (Apache-2.0 + 3 addenda: no separate commercial license needed below 100M MAU / $20M monthly revenue; attribute MinerU if you offer it as an online service) |
| **[GLM / Zhipu AI](https://open.bigmodel.cn/)** | Cloud vision model (`glm-4.6v-flashx`) that replaces MinerU's bundled VLM. Consumes **your GLM quota**, not mineru.net's. | Get a free `GLM_API_KEY` at Zhipu Open Platform | Zhipu AI service terms; `glm-4.6v-flashx` has a free tier |
| **PaddleOCR** (bundled in MinerU) | Local OCR for scanned-page text extraction (hybrid mode). Ships inside the MinerU environment, no separate install. | auto via MinerU | Apache-2.0 |
| **PP-DocLayoutV2** (bundled in MinerU) | Local layout analysis: detects title/paragraph/table/image regions (hybrid mode). | auto-downloaded by MinerU to `models/` | Model card license (opendatalab) |
| **TableMaster / SlanetPlus** (bundled in MinerU) | Local table-structure recognition (hybrid mode). | auto via MinerU | Model card license |
| **UniMERNet** (bundled in MinerU) | Local formula → LaTeX recognition (hybrid mode). | auto via MinerU | Model card license |
| **[PyMuPDF](https://pymupdf.readthedocs.io/)** | Slices PDFs >200 MB into ≤190-page chunks before upload. Used by `mineru_local_batch.py`. | `pip install pymupdf` (only needed for the batch script) | AGPL-3.0 / commercial |

> **Model license note**: the layout/OCR/table/formula models bundled with MinerU
> are separate from MinerU's own code license. Check each model card before
> commercial redistribution. The GLM model is a **cloud API** — you never
> redistribute it, so only Zhipu's service terms apply.

### Environment prerequisites

- A MinerU environment (pip-installed). The scripts locate it via the
  `MGB_MINERU_ENV` env var (default `~/.venv/mineru`).
- Pipeline models for hybrid mode — auto-downloaded on first run, or via
  `mineru-models-download -m pipeline`. Path is configurable in `mineru.json`.
- A Zhipu AI `GLM_API_KEY` (`glm-4.6v-flashx` free tier).
- ~3 GB free system RAM for hybrid mode (local pipeline models run on CPU).

## Support

If this project has helped you in any way, you're welcome to buy me a coffee. It's completely voluntary — the project stays free and open-source regardless. For an independent developer, every small token of appreciation matters.

<p align="center">
  <img src="assets/donate_wechat.jpg" alt="WeChat Pay" width="200">
  <img src="assets/donate_alipay.jpg" alt="Alipay" width="200">
</p>

<p align="center"><i>Thanks for reading all the way down here. 🙏</i></p>

## License

Dual-licensed: [AGPL-3.0](LICENSE) for open source, [commercial](COMMERCIAL.md)
for closed-source use. Third-party tools/models listed above are governed by
their own licenses.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
