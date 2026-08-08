# 变更记录

本文件记录本项目的所有重要变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [0.2.1] - 2026-08-08

### 新增
- **看门狗**（`watchdog.py`）：每 30 秒写心跳 JSON，含 GLM 连接数、10 分钟内新产出、
  `auto_convert` 进程存活、已转块数——供外部监控检测静默卡死或进程死亡。
  路径可用 `MGB_ROOT` / `MGB_PROXY_PORT` / `MGB_HEARTBEAT` 配置。跨平台（Windows PowerShell + Unix pgrep）。

### 修复
- `mineru_local_batch.py` / `auto_convert.py` 输出嵌套：本地 `hybrid-http-client` 模式
  生成 `{文件名}/{backend}/...` 子目录，而非 `{原名}_mineru/full.md`。现已归位为文档规定的结构。

## [0.2.0] - 2026-08-08

## [0.2.0] - 2026-08-08

### 新增
- **自动转换脚本**（`auto_convert.py`）：
  - 按 plan.json `days_normal` 逐天持续转换普通文档
  - 断点续跑（跳过已转换块）+ 进度记录
  - 每 10 块检查点，暂停等人工质量审查
  - 复杂文档记录到 `_mineru_tools/complex_list.md`，供后续云端 API 转换
- **串行稳定配置**：≤16GB 内存机器上互补模式 fork 多 worker 进程耗尽内存。
  强制串行解决：
  - `MINERU_DEVICE_MODE=cpu`、`CUDA_VISIBLE_DEVICES=""`（禁用 GPU → torch/
    PaddleOCR 不会 OOM）
  - `MINERU_PROCESSING_WINDOW_SIZE=2`、`MINERU_API_MAX_CONCURRENT_REQUESTS=1`、
    `MINERU_PDF_RENDER_THREADS=1`、`OMP_NUM_THREADS=1`
  - 实测：串行互补转 109 页约 82 分钟（2页/90秒），内存稳定 ~3.5GB
- **复杂文档预扫描**：标记 PDF 为普通（有文本层）vs 复杂（扫描/图片密集/公式）。
  复杂文档走 mineru.net 云端 API（每天 1000 页）；普通文档用本地 GLM 桥接。

### 变更
- `mineru_local_batch.py` 和 `auto_convert.py` 现在在 `ensure_proxy()` 中自动设置串行配置。
- README（中/英）补充串行配置和普通/复杂分流说明。

### 修复
- 8GB GPU / 16GB 内存笔记本上 hybrid 模式 OOM（worker 进程 + 本地模型超内存）。
- 后台进程被会话销毁杀掉：`auto_convert.py` 和 GLM 代理改为脱离进程（`Start-Process`）。

## [0.1.0] - 2026-08-07

## [0.1.0] - 2026-08-07

### 新增
- **GLM 适配代理**（`glm_mineru_proxy.py`）：
  - 将 MinerU 的 OpenAI 格式 `/v1/chat/completions` 请求桥接到 GLM API
  - 从 MinerU prompt 识别任务类型（版面/表格/公式/文本/图片）
  - 按任务注入格式指令，让 GLM 输出 MinerU 兼容的版面格式
  - 限流（信号量 + 最小间隔）避免 GLM HTTP 429
  - ThreadingHTTPServer 支持 MinerU 多 worker 并发请求
  - 强制直连（绕过系统代理）避免 SSL 抖动
- **批量转换脚本**（`mineru_local_batch.py`）：
  - 自动启动 GLM 代理并配置 MinerU VLM 环境变量
  - 互补模式（本地版面/OCR 模型 + GLM VLM）通过 `hybrid-http-client`
  - 用 PyMuPDF 切片 >200MB 的 PDF
  - 断点续跑（跳过已转换的块）
  - 输出到独立 `{文件名}_mineru/` 子文件夹（不污染源目录）
- **文档**：
  - README.md（英文）/ README_zh.md（中文）
  - CHANGELOG.md / CHANGELOG_zh.md
  - LICENSE（AGPL-3.0 双许可）/ COMMERCIAL.md
  - requirements.txt / .gitignore

### 已验证
- 10 页 PDF：完整管线通过 `vlm-http-client`（纯 GLM）和 `hybrid-http-client`
  （互补模式）运行 —— **不消耗** mineru.net 每日额度，**无需**本地 GPU 显存。
- 互补模式质量：10.2 KB markdown vs 纯 GLM 3.2 KB；OCR 几乎无错别字，
  目录页码对齐，标题层级完整。

### 已知限制
- 互补模式较慢（约 30-60 秒/页：本地 CPU 版面/OCR + GLM 限流）。批量转换
  建议分块、延长运行窗口。
- 纯 GLM 模式的 OCR 偶有错别字（通用视觉模型，非专用 OCR）。
- 互补模式需要约 3 GB 空闲系统内存（本地 pipeline 模型）。
