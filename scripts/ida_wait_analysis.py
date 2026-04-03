# IDAPython: 在 IDA 中直接运行，测量「等待自动分析（含 FLIRT）」耗时并弹窗显示。
# 用法: IDA 菜单 File -> Script file... 选择本文件运行，或 Alt+F7 执行。
# 不依赖 __file__，可在 IDA 内置 Python 中运行。

import time

try:
    import ida_auto
except ImportError:
    ida_auto = None
try:
    import idc
except ImportError:
    idc = None
try:
    import idaapi
except ImportError:
    idaapi = None

def main():
    if ida_auto is None:
        msg = "IDA 未提供 ida_auto 模块，无法等待自动分析。"
        if idc:
            idc.msg(msg + "\n")
        if idaapi:
            idaapi.info(msg)
        return

    t0 = time.perf_counter() if hasattr(time, "perf_counter") else time.clock()
    ida_auto.auto_wait()
    elapsed = (time.perf_counter() if hasattr(time, "perf_counter") else time.clock()) - t0

    msg = "IDA 自动分析（含 FLIRT）等待耗时: {:.2f} 秒".format(elapsed)
    if idc:
        idc.msg(msg + "\n")
    if idaapi:
        idaapi.info(msg)

    if elapsed < 0.01:
        tip = "说明：分析在运行本脚本前已完成，故等待时间为 0。若要测量「打开二进制到分析结束」的总耗时，请用命令行：python scripts/benchmark_ida_flirt.py <二进制路径>"
        if idc:
            idc.msg(tip + "\n")
        if idaapi:
            idaapi.info(tip)

    # 批处理模式（-S 启动）下执行完后退出，便于外部测总时间
    try:
        if getattr(idaapi, "cvar", None) and getattr(idaapi.cvar, "batch", 0):
            if idc:
                idc.qexit(0)
            elif idaapi:
                idaapi.qexit(0)
    except Exception:
        pass

if __name__ == "__main__":
    main()
