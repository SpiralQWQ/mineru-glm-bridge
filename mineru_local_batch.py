#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinerU 本地批量转换脚本 v2（GLM 桥接版）
自动启动 GLM 代理，用 hybrid-http-client（本地专用模型 + 云端 GLM 互补）批量转 PDF → MD

特性：
- 自动启动 GLM 代理（glm_mineru_proxy.py）并配置环境变量
- hybrid-http-client：本地版面/OCR + 云端 GLM VLM 互补（不占 mineru 额度、不吃显存）
- 断点续跑：已完成块自动跳过
- 输出到独立子文件夹，不污染原目录

用法:
  python mineru_local_batch.py                # 转所有未转PDF
  python mineru_local_batch.py --limit N      # 只转前N个文件
  python mineru_local_batch.py --day D        # 仅转计划中 DayD 的块
  python mineru_local_batch.py --dry-run      # 只预览，不执行
  python mineru_local_batch.py --backend vlm-http-client   # 用纯 GLM 模式（质量略低但更快）
"""
import os, sys, json, time, subprocess, socket

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============ 路径配置（全部可用环境变量覆盖） ============
# ROOT: 待转换 PDF 的根目录（含 plan.json 与 _mineru_tools/）
# MINERU_ENV: MinerU 虚拟环境目录
# BRIDGE_DIR: 本桥接项目目录（含 glm_mineru_proxy.py）
ROOT = os.environ.get("MGB_ROOT", os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.environ.get("MGB_TOOLS", os.path.join(ROOT, "_mineru_tools"))
PLAN = os.path.join(TOOLS, "plan.json")
MINERU_ENV = os.environ.get(
    "MGB_MINERU_ENV",
    os.path.join(os.path.expanduser("~"), ".venv", "mineru"))
BRIDGE_DIR = os.environ.get("MGB_BRIDGE_DIR", os.path.dirname(os.path.abspath(__file__)))
PYTHON = os.path.join(MINERU_ENV, "Scripts", "python.exe")
MINERU_CLI = os.path.join(MINERU_ENV, "Scripts", "mineru.exe")
PROXY_SCRIPT = os.path.join(BRIDGE_DIR, "glm_mineru_proxy.py")
PROXY_PORT = int(os.environ.get("MGB_PROXY_PORT", "8031"))
OUTPUT_DIR = os.path.join(ROOT, "_output")

EXTS = ('.pdf', '.pptx', '.doc', '.docx')
TIMEOUT_PER_PAGE = 15
DEFAULT_BACKEND = "hybrid-http-client"  # 互补模式（本地专用模型 + GLM）


def safe(name):
    import re
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def build_plan_from_files():
    """plan.json 缺失时，递归扫描 ROOT 下文档自动生成计划（开箱即用）。

    每文件一块（整篇转换），无分页切块；需要分页/分天调度时再手写 plan.json。
    """
    found = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (os.path.basename(OUTPUT_DIR), os.path.basename(TOOLS))]
        for fn in files:
            if fn.lower().endswith(EXTS):
                found.append(os.path.join(root, fn))
    found.sort()
    if not found:
        return None
    blocks = [{"file": f, "start": 1, "end": 1, "pages": 0} for f in found]
    return {"days_normal": [{"day": 1, "blocks": blocks}]}


def is_done(out_dir):
    if not os.path.isdir(out_dir):
        return False
    if os.path.exists(os.path.join(out_dir, "full.md")):
        return True
    return any(fn.lower().endswith(".json") for fn in os.listdir(out_dir))


def read_token():
    """从用户环境变量读 GLM_API_KEY（Claude Code 子进程读不到 setx 后新值）"""
    try:
        import subprocess
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "[Environment]::GetEnvironmentVariable('GLM_API_KEY','User')"],
            capture_output=True, text=True, timeout=15)
        return r.stdout.strip()
    except Exception:
        return os.environ.get("GLM_API_KEY", "")


def ensure_proxy():
    """确保 GLM 代理在运行"""
    key = read_token()
    if not key:
        print("[错误] 未设置 GLM_API_KEY 环境变量"); sys.exit(1)
    os.environ["GLM_API_KEY"] = key

    # 检查端口是否已监听
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", PROXY_PORT))
        sock.close()
        print(f"[代理] GLM 代理已在运行 (127.0.0.1:{PROXY_PORT})")
    except OSError:
        print(f"[代理] 启动 GLM 代理 (127.0.0.1:{PROXY_PORT})...")
        if not os.path.exists(PROXY_SCRIPT):
            print(f"[错误] 找不到代理脚本: {PROXY_SCRIPT}"); sys.exit(1)
        subprocess.Popen([PYTHON, PROXY_SCRIPT],
                         stdout=open(os.path.join(TOOLS, "proxy.log"), "a", encoding="utf-8"),
                         stderr=subprocess.STDOUT,
                         creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        # 等待端口就绪
        for _ in range(20):
            time.sleep(0.5)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(("127.0.0.1", PROXY_PORT)); s.close()
                print("[代理] 已就绪"); break
            except OSError:
                pass
        else:
            print("[错误] 代理启动超时"); sys.exit(1)

    # 配置 MinerU VLM 环境变量
    os.environ["MINERU_VL_SERVER"] = f"http://127.0.0.1:{PROXY_PORT}"
    os.environ["MINERU_VL_API_KEY"] = key
    os.environ["MINERU_VL_MODEL_NAME"] = "glm-4.6v-flashx"
    # === 串行稳定配置（实测：内存稳定不爆，代价是慢） ===
    os.environ["MINERU_DEVICE_MODE"] = "cpu"          # 设备用 CPU
    os.environ["MINERU_LMDEPLOY_DEVICE"] = "cpu"      # lmdeploy 用 CPU
    os.environ["CUDA_VISIBLE_DEVICES"] = ""           # 强制禁用 GPU，避免 torch/PaddleOCR 占显存 OOM
    os.environ["MINERU_PROCESSING_WINDOW_SIZE"] = "2"  # 每次只处理 2 页（小窗口低内存峰值）
    os.environ["MINERU_API_MAX_CONCURRENT_REQUESTS"] = "1"  # 并发请求 1（串行）
    os.environ["MINERU_PDF_RENDER_THREADS"] = "1"     # PDF 渲染单线程
    os.environ["OMP_NUM_THREADS"] = "1"               # CPU 单线程
    # 绕过系统代理（Clash 对 GLM 的 SSL 抖动）
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)


def chunk_large_pdf(filepath):
    try:
        import fitz
    except ImportError:
        print("[WARN] PyMuPDF 不可用，大文件跳过切片"); return []
    size_mb = os.path.getsize(filepath) / 1048576
    if size_mb <= 200:
        return [filepath]
    base = os.path.splitext(safe(os.path.basename(filepath)))[0]
    src = fitz.open(filepath)
    total_pages = src.page_count
    slice_size = 190
    temp_files = []
    num_slices = (total_pages + slice_size - 1) // slice_size
    for i in range(num_slices):
        out_name = f"d_{base}_p{i*slice_size + 1}-{min((i+1)*slice_size, total_pages)}.pdf"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        dst = fitz.open()
        from_page = i * slice_size
        to_page = min(from_page + slice_size, total_pages) - 1
        dst.insert_pdf(src, from_page=from_page, to_page=to_page)
        dst.save(out_path)
        dst.close()
        temp_files.append(out_path)
    src.close()
    return temp_files or [filepath]


def convert_single(pdf_path, out_dir, backend=DEFAULT_BACKEND):
    cmd = [
        MINERU_CLI, "-p", pdf_path, "-o", out_dir,
        "-m", "auto", "-b", backend,
        "-f", "true", "-t", "true",
    ]
    if "http-client" in backend:
        cmd += ["-u", f"http://127.0.0.1:{PROXY_PORT}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=max(int(len(pdf_path.split()) * TIMEOUT_PER_PAGE), 300))
        if proc.returncode != 0:
            stderr = proc.stderr[-300:] if proc.stderr else "no output"
            print(f"[ERROR] 转换失败 {os.path.basename(pdf_path)}: {stderr}")
            return False
        print(f"[OK] {os.path.basename(pdf_path)} → {out_dir}")
        return True
    except subprocess.TimeoutExpired:
        print(f"[ERROR] 超时: {os.path.basename(pdf_path)}")
        return False


def main():
    args = [a for a in sys.argv[1:]]
    dry_run = "--dry-run" in args
    limit = None
    day = None
    backend = DEFAULT_BACKEND
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    if "--day" in args:
        day = int(args[args.index("--day") + 1])
    if "--backend" in args:
        backend = args[args.index("--backend") + 1]

    if not dry_run:
        ensure_proxy()

    try:
        plan = json.load(open(PLAN, encoding="utf-8"))
    except FileNotFoundError:
        print(f"[提示] 未找到计划文件 {PLAN}")
        print("[提示] 自动扫描 ROOT 下文档生成计划（整篇转换）...")
        plan = build_plan_from_files()
        if plan is None:
            print(f"[错误] {ROOT} 下未找到 {EXTS} 文档，无法批量转换")
            print(f"[说明] 可创建 {PLAN} 指定分块/分天计划（格式见 README「批量转换计划」）")
            sys.exit(1)
        print(f"[提示] 扫描到 {len(plan['days_normal'][0]['blocks'])} 个文档")
    # 兼容新旧 plan 结构：v2 用 days_normal，旧版用 days
    days = plan.get("days_normal") or plan.get("days") or []
    blocks = []
    if day:
        if day <= len(days):
            blocks = days[day - 1]["blocks"]
        else:
            print(f"[Day {day}] 超出范围（共 {len(days)} 天）"); return 0
    else:
        for d in days:
            for b in d["blocks"]:
                blocks.append(b)

    tasks = []
    for i, b in enumerate(blocks):
        if not os.path.exists(b["file"]):
            print(f"  跳过(源文件删除): {os.path.basename(b['file'])} p{b['start']}-{b['end']}")
            continue
        orig_dir = os.path.dirname(b["file"])
        base = safe(os.path.splitext(os.path.basename(b["file"]))[0])
        out_root = os.path.join(orig_dir, base + "_mineru")
        multi = len([x for x in blocks if x["file"] == b["file"]]) > 1
        out_dir = os.path.join(out_root, f"p{b['start']}-{b['end']}") if multi else out_root
        if is_done(out_dir):
            print(f"  跳过(已完成): {os.path.basename(b['file'])} p{b['start']}-{b['end']}")
            continue
        tasks.append({"block": b, "tmp_file": None, "out": out_dir})

    if not tasks:
        print("[Day] 全部已完成"); return 0
    if limit:
        tasks = tasks[:limit]
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total_pages = sum(t["block"]["pages"] for t in tasks)
    print(f"[本地批量] {len(tasks)} 个任务 / {total_pages} 页 / 后端 {backend}")
    print(f"[模式] 本地专用模型(CPU) + 云端 GLM VLM 互补，不占 mineru 额度\n")

    if dry_run:
        for t in tasks:
            bf = t["block"]
            print(f"  [DRY-RUN] {os.path.basename(bf['file'])} → {t['out']}")
        print("\n[DRY-RUN] 完成，未执行。去掉 --dry-run 开始转换"); return 0

    for t in tasks:
        bf = t["block"]
        t["tmp_file"] = chunk_large_pdf(bf["file"])

    success_count = fail_count = 0
    skipped = sum(1 for t in tasks if is_done(t["out"]))
    print(f"\n[执行] {len(tasks) - skipped} 个待转任务...\n")
    for idx, t in enumerate(tasks, 1):
        bf = t["block"]
        tmp_files = t["tmp_file"] if t["tmp_file"] else [bf["file"]]
        for j, tmp in enumerate(tmp_files):
            if convert_single(tmp, t["out"], backend):
                success_count += 1
            else:
                fail_count += 1
        if idx % 5 == 0 or idx == len(tasks):
            print(f"\n进度: {idx}/{len(tasks)} 已完成, 成功 {success_count}, 失败 {fail_count}\n")

    try:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for f in files:
                os.remove(os.path.join(root, f))
        print("\n[清理] 切片临时文件已清除")
    except OSError:
        pass
    print(f"\n[总结] 成功 {success_count}, 失败 {fail_count}, 跳过 {skipped}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    main()
