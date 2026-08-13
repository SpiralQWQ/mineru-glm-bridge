---
name: mineru-glm-bridge
description: MinerU 文档解析 × GLM 云端视觉桥接。用户提到 MinerU 转换、PDF转md、vlm-engine 显存不足、mineru 1000页额度不够时使用。自动启动 GLM 代理，用 hybrid-http-client（本地版面/OCR + GLM VLM 互补）转换，不占 mineru 额度、不吃本地显存。
category: tool
tags: [MinerU, GLM, 文档解析, PDF转Markdown, VLM, 智谱, 版面分析, OCR]
---

# MinerU × GLM 云端视觉桥接

让 MinerU 文档解析接 GLM 云端视觉模型，解决两个真实痛点：
1. 本地 `vlm-engine` 需要 8GB+ 显卡（消费级跑不了）
2. mineru.net 云端每天只有 1000 页免费额度

**方案**：MinerU `vlm-http-client`/`hybrid-http-client` 连 GLM 代理 → GLM 云端视觉，
**不占 mineru 额度、不吃本地显存**。

## 触发方式

用户提到以下任一话题即自动启用本技能：
- MinerU 转换 / PDF 转 Markdown / 文档解析
- vlm-engine 显存不足 / OOM
- mineru 1000 页额度不够 / 想免费转更多

## 快速使用

### 模式一：批量转换（推荐，自动启动代理）

```powershell
cd <本项目目录>            # 例如 cd mineru-glm-bridge
python mineru_local_batch.py --limit 5      # 转前5个文件
python mineru_local_batch.py --day 3        # 转计划中 Day 3
python mineru_local_batch.py --dry-run      # 预览不执行
```

### 模式二：手动单文件

```powershell
# 1. 启动代理
python glm_mineru_proxy.py

# 2. 设置环境变量
set MINERU_VL_SERVER=http://127.0.0.1:8031
set MINERU_VL_API_KEY=%GLM_API_KEY%
set MINERU_VL_MODEL_NAME=glm-4.6v-flashx
set MINERU_LMDEPLOY_DEVICE=cpu
set MINERU_PROCESSING_WINDOW_SIZE=2

# 3. 转换（互补模式质量最高）
mineru -p 文档.pdf -o 输出 -b hybrid-http-client -u http://127.0.0.1:8031
```

## 两种模式选哪个

| 场景 | 用哪个 | 原因 |
|---|---|---|
| 追求最高质量 | `hybrid-http-client` | 本地版面/OCR + GLM 兜底，错别字少 |
| 追求速度 | `vlm-http-client` | 纯 GLM，快但 OCR 有错别字 |
| 扫描版/复杂排版 | `hybrid-http-client` | PaddleOCR 更准 |

## 关键参数（环境变量）

| 变量 | 值 | 作用 |
|---|---|---|
| `GLM_API_KEY` | 智谱Key | 必填 |
| `MINERU_VL_SERVER` | `http://127.0.0.1:8031` | GLM 代理地址 |
| `MINERU_VL_MODEL_NAME` | `glm-4.6v-flashx` | 视觉模型 |
| `MINERU_LMDEPLOY_DEVICE` | `cpu` | 本地不吃显存 |
| `MINERU_PROCESSING_WINDOW_SIZE` | `2` | 限制内存占用 |
| `OMP_NUM_THREADS` | `1` | 限制 CPU 线程（串行） |

## 排障

- **GLM 429**：代理已限流；还出现就增大 `GLM_MIN_INTERVAL`
- **输出 md 空**：看代理日志 `task=` 是否识别正确；GLM 未按格式输出就检查格式指令
- **CUDA OOM**：设 `MINERU_LMDEPLOY_DEVICE=cpu`
- **系统内存不足**：`MINERU_PROCESSING_WINDOW_SIZE=2` + 关闭占内存程序
- **连接失败**：`curl http://127.0.0.1:8031/v1/models` 验证代理存活

## 注意事项

- **GLM 花钱先确认**：flashx 免费额度有限，批量前确认
- **互补模式慢**（30-60秒/页）：分块、延长窗口
- **输出隔离**：`{文件名}_mineru/` 独立子文件夹，不污染源目录
