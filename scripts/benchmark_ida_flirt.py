#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测量 IDA FLIRT 用时：在批处理模式下运行 IDA，加载二进制并等待自动分析（含 FLIRT）完成，统计墙钟时间。
用于与本文方法（表 5b）做效率对比。需本机已安装 IDA Pro 且可执行 idat64/idat。

用法（在 symbol_recovery_system 目录下）:
  python scripts/benchmark_ida_flirt.py <二进制路径> [--ida idat64] [--timeout 600]
  python scripts/benchmark_ida_flirt.py "E:\work\symbol\bin\1.0.2_openssl" --ida "E:\BinXray\IDA_Pro_v8.3_Portable\ida.exe"

说明:
  - 测得的为「IDA 加载二进制 + 自动分析（含 FLIRT 库识别）」的总耗时，与表 5b 中「单函数均时」可比（需除以函数数）。
  - 若需仅测 FLIRT 应用阶段，需在 IDA 脚本内单独计时并写文件，此处为整流程耗时。
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# 当前脚本所在目录，用于解析 ida_wait_analysis.py 的路径（兼容 __file__ 未定义环境）
try:
    _script_path = __file__
except NameError:
    _script_path = sys.argv[0] if sys.argv else os.path.abspath(".")
SCRIPT_DIR = Path(_script_path).resolve().parent
IDA_SCRIPT = SCRIPT_DIR / "ida_wait_analysis.py"


def find_ida(ida_path: str):
    """返回 idat64 或 idat 可执行路径。"""
    if ida_path and os.path.isfile(ida_path):
        return ida_path
    if ida_path and os.path.isdir(ida_path):
        for name in ("idat64", "idat64.exe", "idat", "idat.exe"):
            p = Path(ida_path) / name
            if p.exists():
                return str(p)
    for name in ("idat64", "idat64.exe", "idat", "idat.exe"):
        try:
            r = subprocess.run(
                [name, "--help"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            if r.returncode is not None or b"IDA" in (r.stdout or b"") + (r.stderr or b""):
                return name
        except FileNotFoundError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description="测量 IDA（含 FLIRT）加载+分析二进制用时")
    parser.add_argument("binary", help="待分析的二进制文件路径")
    parser.add_argument("--ida", default="", help="IDA 可执行路径或安装目录（默认自动查找 idat64/idat）")
    parser.add_argument("--timeout", type=int, default=600, help="最大运行秒数（默认 600）")
    parser.add_argument("--out", default="", help="将耗时(秒)写入该文件（一行浮点数）")
    args = parser.parse_args()

    binary = Path(args.binary)
    if not binary.exists():
        print(f"错误: 二进制不存在: {binary}", file=sys.stderr)
        return 1

    ida_exe = find_ida(args.ida)
    if not ida_exe:
        print("错误: 未找到 idat64/idat，请安装 IDA Pro 或将 --ida 指向可执行文件或安装目录。", file=sys.stderr)
        return 1

    if not IDA_SCRIPT.exists():
        print(f"错误: 未找到 IDA 脚本: {IDA_SCRIPT}", file=sys.stderr)
        return 1

    cmd = [
        ida_exe,
        "-A",
        "-S" + str(IDA_SCRIPT),
        str(binary.resolve()),
    ]
    print(f"运行: {' '.join(cmd)}")
    print("等待 IDA 加载并完成自动分析（含 FLIRT）...")
    t0 = time.perf_counter()
    try:
        env = os.environ.copy()
        env["TVHEADLESS"] = "1"
        r = subprocess.run(
            cmd,
            cwd=str(SCRIPT_DIR),
            timeout=args.timeout,
            capture_output=True,
            text=True,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        elapsed = time.perf_counter() - t0
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        print(f"超时（{args.timeout} s）后终止。已用时间: {elapsed:.2f} s", file=sys.stderr)
        if args.out:
            Path(args.out).write_text(f"{elapsed:.2f}\n", encoding="utf-8")
        return 124
    except Exception as e:
        print(f"运行 IDA 失败: {e}", file=sys.stderr)
        return 1

    print(f"IDA FLIRT（加载+自动分析）耗时: {elapsed:.2f} s")
    if r.returncode != 0:
        print(f"IDA 退出码: {r.returncode}", file=sys.stderr)
        if r.stderr:
            print(r.stderr[:500], file=sys.stderr)
    if args.out:
        Path(args.out).write_text(f"{elapsed:.2f}\n", encoding="utf-8")
        print(f"已写入: {args.out}")
    return 0 if r.returncode == 0 else r.returncode


if __name__ == "__main__":
    sys.exit(main())
