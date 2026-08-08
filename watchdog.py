#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mineru-glm-bridge 看门狗 — 检测转换是否卡死/推进，写心跳文件供外部监控

监控指标:
  1. GLM 代理连接数（>0 = 在调 GLM）
  2. 输出目录 full.md 数量（产出增长）
  3. auto_progress converted 计数
  4. auto_convert 进程存活
  5. 心跳时间戳（检测卡死：无心跳超时 = 卡住）

环境变量:
  MGB_ROOT          待转换 PDF 根目录（含 _mineru_tools/），默认脚本所在目录
  MGB_PROXY_PORT    GLM 代理端口，默认 8031
  MGB_HEARTBEAT     心跳文件路径，默认 <ROOT>/_mineru_tools/watchdog_heartbeat.json

用法: python watchdog.py
"""
import os, sys, json, time, subprocess, glob

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.environ.get("MGB_ROOT", os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "_mineru_tools")
HEARTBEAT = os.environ.get(
    "MGB_HEARTBEAT", os.path.join(TOOLS, "watchdog_heartbeat.json"))
PROGRESS = os.path.join(TOOLS, "auto_progress.json")
PROXY_PORT = os.environ.get("MGB_PROXY_PORT", "8031")

STALE_SECONDS = 900  # 15分钟


def check_glm_conns():
    """统计 ESTABLISHED 到代理端口的连接数"""
    try:
        r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=10)
        conns = 0
        for line in r.stdout.splitlines():
            if f"127.0.0.1:{PROXY_PORT}" in line and "ESTABLISHED" in line:
                conns += 1
        return conns
    except Exception:
        return -1


def count_outputs():
    """统计所有 _mineru 目录里最近的 full.md（10分钟内）"""
    try:
        now = time.time()
        fresh = 0
        for md in glob.glob(os.path.join(ROOT, "**", "*_mineru", "full.md"), recursive=True):
            if now - os.path.getmtime(md) < 600:
                fresh += 1
        return fresh
    except Exception:
        return -1


def _proc_running_win(cmd):
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f"Get-CimInstance Win32_Process | Where-Object {{$_.CommandLine -match '{cmd}' -and $_.Name -match 'python'}} | Select-Object -First 1"],
            capture_output=True, text=True, timeout=15)
        return "ProcessId" in r.stdout
    except Exception:
        return False


def _proc_running_unix(cmd):
    try:
        r = subprocess.run(["pgrep", "-f", cmd], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def check_process(cmd="auto_convert"):
    """检测 auto_convert 进程存活（跨平台）"""
    if sys.platform == "win32":
        return _proc_running_win(cmd)
    return _proc_running_unix(cmd)


def main():
    print(f"[watchdog] 监控 {ROOT} | 代理 {PROXY_PORT} | 心跳 {HEARTBEAT}")
    while True:
        conns = check_glm_conns()
        fresh = count_outputs()
        alive = check_process()
        conv = 0
        if os.path.exists(PROGRESS):
            try:
                conv = json.load(open(PROGRESS, encoding="utf-8")).get("converted", 0)
            except:
                pass
        status = {
            "ts": time.time(),
            "glm_conns": conns,
            "fresh_outputs_10min": fresh,
            "process_alive": alive,
            "converted": conv,
        }
        json.dump(status, open(HEARTBEAT, "w", encoding="utf-8"), ensure_ascii=False)
        time.sleep(30)


if __name__ == "__main__":
    main()
