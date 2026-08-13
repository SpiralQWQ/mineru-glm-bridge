# CLAUDE.md — mineru-glm-bridge 项目配置

> **安装**：复制本文件到项目根目录并重命名为 `CLAUDE.md`；按 `SKILL.md` 安装技能。
> 本文件是模板，按需裁剪。
>
> 项目：MinerU-GLMBridge · 双许可（AGPL-3.0 / 商业授权）

## 基础规则

- 始终用**中文**回复，回答简洁结构化。
- 编辑前先读懂现有结构和代码风格，不做超出任务范围的抽象或重构。
- 英文术语保留，附中文简要说明。
- 本项目是工具类仓库，可依实际工作流裁剪章节。

## 项目定位

MinerU 文档解析 × GLM 云端视觉桥接。让普通笔记本无需 8GB+ 显卡、不消耗
mineru.net 每日 1000 页额度，即可完整运行 MinerU 文档解析（PDF → Markdown）。

## 核心能力

| 模式 | 后端 | 说明 |
|---|---|---|
| 纯 GLM | `vlm-http-client` | 最快；OCR 可能有错别字 |
| **互补（推荐）** | `hybrid-http-client` | 本地版面/OCR + GLM VLM 兜底，质量最高 |

## 使用流程

### 1. 启动 GLM 代理

```powershell
setx GLM_API_KEY "你的智谱Key"
python glm_mineru_proxy.py
```

### 2. 配置 MinerU 环境变量并转换

```powershell
set MINERU_VL_SERVER=http://127.0.0.1:8031
set MINERU_VL_API_KEY=%GLM_API_KEY%
set MINERU_VL_MODEL_NAME=glm-4.6v-flashx
set MINERU_LMDEPLOY_DEVICE=cpu
set MINERU_PROCESSING_WINDOW_SIZE=2
mineru -p 文档.pdf -o 输出 -b hybrid-http-client -u http://127.0.0.1:8031
```

### 3. 批量转换（自动启动代理）

```powershell
python mineru_local_batch.py --limit 5      # 转前5个文件
python mineru_local_batch.py --day 3        # 转计划中 Day 3
python mineru_local_batch.py --dry-run      # 预览不执行
```

## 关键约束

- **GLM 花钱必须用户确认**：GLM-4.6v-flashx 免费额度有限，批量任务前确认额度。
- **不占 mineru 额度**：VLM 走 GLM 云端，不消耗 mineru.net 的 1000 页/天。
- **本地不吃显存**：本地模型用 CPU（`MINERU_LMDEPLOY_DEVICE=cpu`）。
- **互补模式慢**：约 30-60 秒/页，批量需分块、延长运行窗口。
- **输出隔离**：每文件 → `{文件名}_mineru/` 独立子文件夹，不污染源目录。

## 排障速查

| 问题 | 解决 |
|---|---|
| GLM HTTP 429 | 代理已限流；若仍出现，增大 `GLM_MIN_INTERVAL` 间隔 |
| MinerU 连不上代理 | 确认代理在 127.0.0.1:8031，`curl http://127.0.0.1:8031/v1/models` |
| 输出 md 为空 | 多为 GLM 未按格式输出，看代理日志 `task=` 是否正确识别 |
| CUDA OOM | 设 `MINERU_LMDEPLOY_DEVICE=cpu` |
| 系统内存不足 | 设 `MINERU_PROCESSING_WINDOW_SIZE=2` + 关闭占内存程序 |

## 质量校验

转换后抽查 `full.md`：
- OCR 错别字多 → 用互补模式（hybrid）而非纯 GLM
- 表格乱/公式丢 → 确认 `-t true -f true` 已开启
- 目录页码错 → 互补模式自动修正

## 参考

- 架构/质量对比：`README.md` / `README_zh.md`
- 变更记录：`CHANGELOG.md` / `CHANGELOG_zh.md`
- 商业授权：`COMMERCIAL.md`
