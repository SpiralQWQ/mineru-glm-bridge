# 变更记录

本文件记录本项目的所有重要变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

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
