#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从源码编译「多优化级别」（及可选多架构）二进制，用于跨优化/跨架构实验。
输出目录结构供 Ghidra 导出符号与特征后，用 generate_cross_manifest.py 生成 manifest。

**环境**：建议在 Linux 或 WSL 下运行（需 gcc、make、git）。Windows 原生无 make 时可使用
  WSL 或 Docker（见文档 跨架构与LLM-RAG增强设计.md）。

用法:
  # 仅当前架构，O0～O3 各一份（默认 coreutils）
  python scripts/build_cross_binaries.py -o data/cross_build

  # 指定项目与优化级别
  python scripts/build_cross_binaries.py -o data/cross_build --projects coreutils --opts O0 O1 O2 O3

  # 多架构需事先安装交叉编译工具链并设置 CC（示例）
  # CC=arm-linux-gnueabi-gcc python scripts/build_cross_binaries.py -o data/cross_build --arch arm32
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# 项目名 -> 克隆 URL；编译后主程序名可能不同
PROJECTS = {
    "coreutils": {
        "url": "https://github.com/coreutils/coreutils.git",
        "branch": "v9.4",
        "binary_name": "src/coreutils",  # 编译后单个大二进制，或逐条 src/ls, src/cp...
        "single_binary": False,  # coreutils 编出很多小二进制在 src/ 下
        "build_script": None,  # 用标准 configure + make
    },
}

DEFAULT_OPTS = ["O0", "O1", "O2", "O3"]
OPT_FLAGS = {"O0": "-O0", "O1": "-O1", "O2": "-O2", "O3": "-O3"}


def run(cmd, cwd=None, env=None, check=True):
    e = os.environ.copy()
    if env:
        e.update(env)
    r = subprocess.run(cmd, shell=True, cwd=cwd, env=e)
    if check and r.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    return r


def detect_arch():
    try:
        out = subprocess.check_output(["uname", "-m"], text=True).strip().lower()
        if "x86_64" in out or "amd64" in out:
            return "x86_64"
        if "aarch64" in out or "arm64" in out:
            return "aarch64"
        if "arm" in out:
            return "arm32"
        if "mips" in out:
            return "mips32"
        return out.replace("/", "_") or "unknown"
    except Exception:
        return "unknown"


def build_project(project_key: str, out_root: Path, opt: str, arch: str, clone_dir: Path):
    info = PROJECTS.get(project_key)
    if not info:
        raise ValueError(f"Unknown project: {project_key}")
    url = info["url"]
    branch = info.get("branch", "master")
    opt_flag = OPT_FLAGS.get(opt, "-O0")

    # 克隆或更新
    if not clone_dir.exists():
        run(f"git clone --depth 1 -b {branch} {url} {clone_dir}")
    else:
        run(f"git fetch --depth 1 origin {branch} && git checkout {branch}", cwd=clone_dir)

    build_dir = clone_dir
    # configure
    if not (build_dir / "configure").exists():
        run("autoreconf -i || true", cwd=build_dir)
    run(
        f'./configure --disable-gcc-warnings CFLAGS="{opt_flag}" CXXFLAGS="{opt_flag}"',
        cwd=build_dir,
    )
    run("make -j$(nproc 2>/dev/null || echo 2)", cwd=build_dir)

    # 输出目录：out_root / project / arch / opt
    out_dir = out_root / project_key / arch / opt
    out_dir.mkdir(parents=True, exist_ok=True)

    # coreutils: 每个可执行文件单独子目录，便于 Ghidra 按「一个二进制」导出符号/特征
    src_dir = build_dir / "src"
    if src_dir.exists():
        for f in src_dir.iterdir():
            if f.is_file() and os.access(f, os.X_OK):
                unit_dir = out_dir / f.name
                unit_dir.mkdir(parents=True, exist_ok=True)
                dest_bin = unit_dir / f.name
                shutil.copy2(f, dest_bin)
                stripped = unit_dir / f"{f.name}.stripped"
                run(f"strip -s {dest_bin} -o {stripped}")
    else:
        # 单二进制项目
        binary_name = info.get("binary_name", "src/coreutils")
        src_bin = build_dir / binary_name
        if src_bin.exists():
            name = Path(binary_name).name
            unit_dir = out_dir / name
            unit_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_bin, unit_dir / name)
            run(f"strip -s {unit_dir / name} -o {unit_dir / (name + '.stripped')}")
        else:
            raise FileNotFoundError(f"Expected binary not found: {src_bin}")

    return out_dir


def main():
    parser = argparse.ArgumentParser(
        description="从源码编译多优化级别二进制，用于跨优化/跨架构实验"
    )
    parser.add_argument(
        "-o", "--out-dir", default="data/cross_build", help="输出根目录（默认 data/cross_build）"
    )
    parser.add_argument(
        "--projects", nargs="+", default=["coreutils"], help="要编译的项目（默认 coreutils）"
    )
    parser.add_argument(
        "--opts", nargs="+", default=DEFAULT_OPTS, help="优化级别（默认 O0 O1 O2 O3）"
    )
    parser.add_argument(
        "--arch", default=None, help="架构标签（默认自动检测 uname -m）"
    )
    parser.add_argument(
        "--clone-dir", default=None, help="克隆源码的目录（默认 out_dir/_sources）"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="只打印将要执行的步骤，不执行"
    )
    args = parser.parse_args()

    out_root = Path(args.out_dir).resolve()
    arch = args.arch or detect_arch()
    clone_base = Path(args.clone_dir) if args.clone_dir else (out_root / "_sources")
    clone_base.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32" and not os.environ.get("WSL_DISTRO_NAME"):
        print("提示：当前为 Windows 且未检测到 WSL。编译需 make/gcc，建议在 WSL 或 Linux 下运行本脚本。")
        print("若已安装 MSYS2/MinGW 且 make/gcc 在 PATH 中，可继续尝试。")

    built = []
    for project in args.projects:
        if project not in PROJECTS:
            print(f"跳过未知项目: {project}")
            continue
        clone_dir = clone_base / project
        for opt in args.opts:
            if opt not in OPT_FLAGS:
                print(f"跳过未知优化: {opt}")
                continue
            if args.dry_run:
                print(f"[dry-run] build {project} {arch} {opt} -> {out_root / project / arch / opt}")
                built.append(out_root / project / arch / opt)
                continue
            try:
                d = build_project(project, out_root, opt, arch, clone_dir)
                built.append(d)
                print(f"已构建: {d}")
            except Exception as e:
                print(f"构建失败 {project} {arch} {opt}: {e}")
                raise

    readme = out_root / "README_下一步.txt"
    with open(readme, "w", encoding="utf-8") as f:
        f.write("跨架构/跨优化实验 - 二进制已生成\n")
        f.write("=" * 50 + "\n\n")
        f.write("目录结构：<out>/<项目>/<架构>/<优化>/<可执行名>/ 下有 可执行名 与 可执行名.stripped。\n\n")
        f.write("下一步：对上述每个「可执行名」目录：\n")
        f.write("  1) 用 Ghidra 对有符号二进制导出符号 -> 该目录下 symbols.json\n")
        f.write("  2) 用 Ghidra 对 .stripped 导出特征 -> 该目录下 features.json\n\n")
        f.write("然后运行：\n")
        f.write("  python scripts/generate_cross_manifest.py -d " + str(out_root) + "\n\n")
        f.write("得到 manifest.json 后，用 prepare_self_eval_multi 做自对比评估。\n")
    print(f"已写入说明: {readme}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
