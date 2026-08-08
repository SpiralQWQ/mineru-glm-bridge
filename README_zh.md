# MinerU-GLMBridge

将 MinerU 文档解析桥接到 GLM（智谱 AI）云端视觉模型 —— 让普通笔记本无需 8GB+ 显卡，
也不消耗 mineru.net 每日 1000 页额度，即可完整运行 MinerU 文档解析。

## 解决什么问题

| 痛点 | MinerU-GLMBridge |
|---|---|
| 本地 `vlm-engine` 需要 8GB+ GPU 显存 | ✅ 任意笔记本可跑（VLM 在云端） |
| mineru.net 云端每天只有 1000 页免费额度 | ✅ 改用 GLM 自己的额度 |
| 扫描版 PDF 的本地 OCR 质量 | ✅ 互补模式：本地 PaddleOCR + GLM VLM |

## 两种模式

| 模式 | 后端 | 质量 | 说明 |
|---|---|---|---|
| 纯 GLM | `vlm-http-client` | ★★★★ | 最快；OCR 可能有错别字（通用视觉模型） |
| **互补（推荐）** | `hybrid-http-client` | ★★★★★ | 本地版面/OCR 模型 + GLM VLM 兜底 |

## 架构

```
MinerU (vlm-http-client / hybrid-http-client)
  ├─ 版面分析（本地 PP-DocLayoutV2）
  ├─ OCR/表格/公式（本地 PaddleOCR、TableMaster）  [仅互补模式]
  └─ VLM 兜底 ──► GLM 适配代理（本仓库）
                      │  监听 127.0.0.1:8031
                      │  识别任务类型，注入格式指令
                      │  限流避免 HTTP 429
                      ▼
             GLM-4.6V 云端视觉（走 GLM 额度）
```

## 文件说明

| 文件 | 作用 |
|---|---|
| `glm_mineru_proxy.py` | GLM 适配代理：MinerU OpenAI 格式请求 → GLM API，按任务注入格式指令，串行限流 |
| `mineru_local_batch.py` | 批量转换：自动启动代理、切片 PDF、调 MinerU、输出独立子文件夹 |

## 安装（开箱即用步骤）

按顺序执行，每步写清楚**要下载什么**。

### 下载清单（一目了然）

| # | 下载/获取 | 用途 | 来源 |
|---|---|---|---|
| 1 | 本仓库 | 代码 | `git clone`（见下） |
| 2 | Python 3.10+ | 运行脚本 | python.org |
| 3 | **MinerU**（含模型） | 文档解析引擎 | `pip install "mineru[all]"` |
| 4 | **GLM API Key**（免费） | 云端视觉模型 | 智谱开放平台 |
| 5 | PyMuPDF | 切分 >200MB 的 PDF | `pip install pymupdf` |

### 第一步 — 克隆本仓库

```bash
git clone https://github.com/SpiralQWQ/mineru-glm-bridge.git
cd mineru-glm-bridge
```

### 第二步 — 安装 Python 3.10+

从 [python.org](https://www.python.org/downloads/) 下载安装。验证：`python --version`。

### 第三步 — 安装 MinerU（文档解析引擎）

```bash
# 建独立虚拟环境（推荐）
python -m venv .venv-mineru
.venv-mineru\Scripts\activate        # Windows
source .venv-mineru/bin/activate     # Linux/macOS

# 安装 MinerU（首次运行自动下载 OCR/表格/公式模型）
pip install "mineru[all]"
```

首次运行会自动下载 pipeline 模型（约 2 GB）到 `models/`。若失败可显式下载：

```bash
mineru-models-download -m pipeline
```

### 第四步 — 免费申请 GLM API Key

1. 注册 [智谱 AI 开放平台](https://open.bigmodel.cn/)
2. 创建 API Key（`glm-4.6v-flashx` 有免费额度）
3. 设置：

```bash
setx GLM_API_KEY "你的智谱Key"    # Windows
export GLM_API_KEY="你的智谱Key"  # Linux/macOS
```

### 第五步 — 安装 PyMuPDF（批量脚本需要）

```bash
pip install pymupdf
```

仅用 `mineru_local_batch.py` 时需要（它把 >200MB 的 PDF 切片）。

### 第六步 — 告诉脚本 MinerU 在哪（可选）

批量脚本默认在 `~/.venv/mineru` 找 MinerU。若装在别处，设 `MGB_MINERU_ENV`：

```bash
setx MGB_MINERU_ENV "C:\你的\MinerU环境路径"   # Windows
export MGB_MINERU_ENV="/你的/MinerU环境路径"   # Linux/macOS
```

---

## 快速开始

装好后开始转换：

```bash
# 1. 启动 GLM 代理
python glm_mineru_proxy.py

# 2. 纯 GLM 模式（最快；OCR 可能有错别字）
set MINERU_VL_SERVER=http://127.0.0.1:8031
set MINERU_VL_API_KEY=%GLM_API_KEY%
set MINERU_VL_MODEL_NAME=glm-4.6v-flashx
mineru -p 文档.pdf -o 输出 -b vlm-http-client -u http://127.0.0.1:8031

# 3. 互补模式（质量更高：本地 OCR + GLM VLM）
set MINERU_LMDEPLOY_DEVICE=cpu
set MINERU_PROCESSING_WINDOW_SIZE=2
mineru -p 文档.pdf -o 输出 -b hybrid-http-client -u http://127.0.0.1:8031
```

或用批量脚本（自动启动代理、切片、断点续跑）：

```bash
setx MGB_MINERU_ENV "C:\你的\MinerU环境路径"
python mineru_local_batch.py --limit 5
```

## 串行稳定配置（≤16GB 内存的关键）

互补模式会 fork 多个 worker 进程，低内存机器会内存耗尽。**强制串行处理**——
更慢但内存稳定：

```bash
set MINERU_DEVICE_MODE=cpu
set CUDA_VISIBLE_DEVICES=               # 禁用 GPU → torch/PaddleOCR 不会 OOM
set MINERU_LMDEPLOY_DEVICE=cpu
set MINERU_PROCESSING_WINDOW_SIZE=2     # 每次只处理 2 页
set MINERU_API_MAX_CONCURRENT_REQUESTS=1  # 串行（并发1）
set MINERU_PDF_RENDER_THREADS=1
set OMP_NUM_THREADS=1
```

> 实测：串行互补模式转 109 页 PDF 约 82 分钟（2 页/约 90 秒），内存稳定 ~3.5GB。
> `auto_convert.py` 会自动设置以上全部变量。

## 复杂文档分流（云端 vs 本地）

转换前预扫描把每份 PDF 标记为**普通**（有文本层、图片少）或**复杂**
（扫描件 / 图片密集 / 数学公式）：

| 类型 | 判定 | 转换方式 |
|---|---|---|
| 普通 | 有文本层 | 本地 hybrid-http-client（免费，本仓库） |
| **复杂** | 无文本层 / 图片密集 / 公式 | mineru.net 云端 API（每天 1000 页额度） |

`auto_convert.py` 自动跳过复杂块并记录到 `_mineru_tools/complex_list.md`，
后续用 `mineru_day.py --complex` 走云端额度转换。

## 质量对比（实测 10 页 PDF）

| 指标 | 纯 GLM | 互补 |
|---|---|---|
| Markdown 大小 | 3.2 KB | 10.2 KB |
| OCR 错别字 | 有 | 几乎无 |
| 目录页码 | 乱 | 对齐 |
| 标题层级 | 部分 | 完整 |

## 依赖工具

MinerU-GLMBridge **不重复实现**文档解析——它编排下面这些成熟工具。每个工具都有自己的许可与条款：

| 工具 | 在本项目中的角色 | 安装 | 许可 |
|---|---|---|---|
| **[MinerU](https://github.com/opendatalab/MinerU)** | 文档解析引擎：PDF→Markdown。提供本桥接连接的 `vlm-http-client` / `hybrid-http-client` 后端。 | `pip install mineru[all]`（推荐 v3.x） | [MinerU Open Source License](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md)（Apache-2.0 + 3 条附加条款：低于 1 亿 MAU / 月收入 2000 万美元无需单独商业许可；若提供在线服务需标明用了 MinerU） |
| **[GLM / 智谱 AI](https://open.bigmodel.cn/)** | 云端视觉模型（`glm-4.6v-flashx`），替换 MinerU 自带的 VLM。消耗**你的 GLM 额度**，不碰 mineru.net 的。 | 智谱开放平台免费申请 `GLM_API_KEY` | 智谱服务条款；`glm-4.6v-flashx` 有免费额度 |
| **PaddleOCR**（MinerU 内置） | 本地 OCR：扫描件文字提取（互补模式）。随 MinerU 环境自带，无需单独安装。 | MinerU 自动 | Apache-2.0 |
| **PP-DocLayoutV2**（MinerU 内置） | 本地版面分析：检测标题/段落/表格/图片区域（互补模式）。 | MinerU 自动下载到 `models/` | 模型卡片许可（opendatalab） |
| **TableMaster / SlanetPlus**（MinerU 内置） | 本地表格结构识别（互补模式）。 | MinerU 自动 | 模型卡片许可 |
| **UniMERNet**（MinerU 内置） | 本地公式 → LaTeX 识别（互补模式）。 | MinerU 自动 | 模型卡片许可 |
| **[PyMuPDF](https://pymupdf.readthedocs.io/)** | 把 >200MB 的 PDF 切成 ≤190 页的分块后上传。供 `mineru_local_batch.py` 使用。 | `pip install pymupdf`（仅批量脚本需要） | AGPL-3.0 / 商业 |

> **模型许可提示**：MinerU 内置的版面/OCR/表格/公式模型与 MinerU 代码本身的许可**相互独立**。商用再分发前请逐个查看模型卡片。GLM 是**云端 API**——你不会再分发它，只需遵守智谱服务条款。

### 环境前提

- MinerU 环境（pip 安装）。脚本通过环境变量 `MGB_MINERU_ENV` 定位（默认 `~/.venv/mineru`）。
- 互补模式需要 pipeline 模型——首次运行自动下载，或用 `mineru-models-download -m pipeline`。路径可在 `mineru.json` 配置。
- 智谱 `GLM_API_KEY`（`glm-4.6v-flashx` 免费额度）。
- 互补模式需约 3 GB 空闲系统内存（本地 pipeline 模型跑 CPU）。

## 💛 支持一下

如果这个项目帮到过你，可以请我喝杯咖啡 ☕。打赏全凭心意，不打赏也完全没关系——项目永远免费开源。做开源这么久，每一份小小的支持都能让我高兴很久。

<p align="center">
  <img src="assets/donate_wechat.jpg" alt="微信收款" width="200">
  <img src="assets/donate_alipay.jpg" alt="支付宝收款" width="200">
</p>

<p align="center"><i>能一路读到这里的你，谢谢。🙏</i></p>

## 许可

双许可：[AGPL-3.0](LICENSE) 开源 + [商业授权](COMMERCIAL.md) 闭源。
上表所列第三方工具/模型受其自身许可约束。

## 变更记录

见 [CHANGELOG_zh.md](CHANGELOG_zh.md)。
