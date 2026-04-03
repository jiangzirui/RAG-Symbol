## ###
# 从外部符号文件恢复符号到当前程序（Ghidra 版，原 IDA 脚本移植）
# 符号文件格式：前 8 字节后为符号表，每项 8 字节 [flag(1), string_offset(3), target_address(4)]；其后为字符串表
# @category: Symbol Recovery
# @runtime PyGhidra

"""
从自定义符号文件（如 VxWorks sym 文件）读取符号并应用到当前打开的二进制。

用法：
  1. 在 Ghidra 中打开**无符号**二进制（File -> Import File）。
  2. 修改本脚本顶部 SYMFILE_PATH、SYMBOLS_TABLE_START、STRINGS_TABLE_START（与您 IDA 脚本一致）。
  3. 在 Ghidra 中运行此脚本：Script Manager -> 找到本脚本 -> Run。
  4. 运行后当前程序即带符号，可导出符号与特征（有符号版本）；原磁盘上的无符号文件即无符号版本，用于自对比评估。

若符号文件路径或表偏移不同，请直接改脚本内常量后重新运行。
"""

import binascii

# Ghidra API
from ghidra.program.model.symbol import SourceType
from ghidra.program.model.address import AddressSet
from ghidra.app.cmd.function import CreateFunctionCmd

# 可修改：符号文件路径与表偏移（与您 IDA 脚本一致）
SYMFILE_PATH = r"E:\work\vx\15CBBA"
SYMBOLS_TABLE_START = 8
STRINGS_TABLE_START = 0x1a728

# 地址偏移：符号文件中的 target_address 会加上此值再在 Ghidra 中查找。
# 若 Ghidra 加载基址与符号文件假设的基址不同，设为二者之差（Ghidra 基址 - 符号文件基址）。
# 例如符号文件里地址是 0x100~0x8000，Ghidra 中程序在 0x10000~0x18f00，则设 ADDRESS_OFFSET = 0xff00。
ADDRESS_OFFSET = 0


def get_string_by_offset(strings_table, offset):
    index = 0
    while offset + index < len(strings_table):
        b = strings_table[offset + index]
        if isinstance(b, str):
            b = ord(b)
        if b == 0:
            break
        index += 1
    chunk = strings_table[offset:offset + index]
    if isinstance(chunk, str):
        return chunk.encode('latin1') if hasattr(chunk, 'encode') else bytes(ord(c) for c in chunk)
    return bytes(chunk) if hasattr(chunk, '__iter__') and not isinstance(chunk, bytes) else chunk


def get_symbols_metadata(symfile_path, symbols_table_start, strings_table_start):
    with open(symfile_path, 'rb') as f:
        symfile_contents = f.read()
    symbols_table = symfile_contents[symbols_table_start:strings_table_start]
    strings_table = symfile_contents[strings_table_start:]
    if isinstance(strings_table, str):
        strings_table = bytearray(strings_table)
    symbols = []
    for offset in range(0, len(symbols_table), 8):
        symbol_item = symbols_table[offset:offset + 8]
        if len(symbol_item) < 8:
            break
        flag = ord(symbol_item[0]) if isinstance(symbol_item[0], str) else symbol_item[0]
        string_offset = int(binascii.b2a_hex(symbol_item[1:4]).decode('ascii'), 16)
        try:
            raw = get_string_by_offset(strings_table, string_offset)
            string_name = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw
        except Exception:
            string_name = "sub_0x%x" % (int(binascii.b2a_hex(symbol_item[4:8]).decode('ascii'), 16))
        target_address = int(binascii.b2a_hex(symbol_item[4:8]).decode('ascii'), 16)
        symbols.append((flag, string_name, target_address))
    return symbols


def add_symbols_ghidra(program, symbols_metadata, address_offset=0):
    addr_factory = program.getAddressFactory()
    default_space = addr_factory.getDefaultAddressSpace()
    symbol_table = program.getSymbolTable()
    function_manager = program.getFunctionManager()
    memory = program.getMemory()

    created_labels = 0
    created_functions = 0
    skipped_not_in_memory = 0
    skipped_bad_name = 0

    for flag, string_name, target_address in symbols_metadata:
        effective_addr = target_address + address_offset
        try:
            addr = default_space.getAddress(effective_addr)
        except Exception:
            try:
                addr = addr_factory.getAddress(default_space.getSpaceID(), effective_addr)
            except Exception:
                continue

        if not memory.contains(addr):
            skipped_not_in_memory += 1
            continue

        name = string_name.strip()
        if not name or name.startswith("?"):
            skipped_bad_name += 1
            continue

        # 非法字符替换（Ghidra 符号名限制）
        for c in [' ', '\\', '/', ':', '*', '?', '"', '<', '>', '|', '\t', '\n', '\r']:
            name = name.replace(c, '_')
        if not name or name[0].isdigit():
            name = "sym_" + name

        try:
            existing = symbol_table.getPrimarySymbol(addr) if hasattr(symbol_table, 'getPrimarySymbol') else symbol_table.getSymbol(addr)
            if existing and existing.getName() and existing.getName() != name:
                existing.setName(name, SourceType.USER_DEFINED)
            elif not existing or not existing.getName() or existing.getName() in ("", "UNKNOWN"):
                symbol_table.createLabel(addr, name, SourceType.USER_DEFINED)
            created_labels += 1
        except Exception as e:
            print("创建标签失败 @ 0x%x: %s" % (target_address, e))
            continue

        if flag == 0x54:
            try:
                func_at = function_manager.getFunctionContaining(addr)
                if not func_at:
                    cmd = CreateFunctionCmd(addr)
                    if cmd.applyTo(program):
                        created_functions += 1
                    func_at = function_manager.getFunctionAt(addr)
                if func_at and func_at.getName() != name:
                    func_at.setName(name, SourceType.USER_DEFINED)
            except Exception:
                pass

    return created_labels, created_functions, skipped_not_in_memory, skipped_bad_name


if __name__ == "__main__":
    program = currentProgram
    symfile_path = SYMFILE_PATH
    symbols_table_start = SYMBOLS_TABLE_START
    strings_table_start = STRINGS_TABLE_START
    address_offset = ADDRESS_OFFSET

    print("符号文件: %s" % symfile_path)
    print("符号表起始: %d, 字符串表起始: 0x%x, 地址偏移: 0x%x" % (symbols_table_start, strings_table_start, address_offset))

    try:
        symbols_metadata = get_symbols_metadata(symfile_path, symbols_table_start, strings_table_start)
    except Exception as e:
        print("读取符号文件失败: %s" % e)
        symbols_metadata = []

    if not symbols_metadata:
        print("无符号可应用，请检查路径与表偏移。")
    else:
        mem = program.getMemory()
        try:
            prog_min = mem.getMinAddress().getOffset()
            prog_max = mem.getMaxAddress().getOffset()
        except Exception:
            prog_min = prog_max = 0
        sym_addrs = [t[2] for t in symbols_metadata]
        sym_min = min(sym_addrs)
        sym_max = max(sym_addrs)
        print("解析到 %d 条符号；符号地址范围: 0x%x ~ 0x%x" % (len(symbols_metadata), sym_min, sym_max))
        print("当前程序内存范围: 0x%x ~ 0x%x" % (prog_min, prog_max))

        created_labels, created_functions, skipped_not_in_memory, skipped_bad_name = add_symbols_ghidra(
            program, symbols_metadata, address_offset
        )
        print("已创建/更新标签: %d, 已创建函数: %d" % (created_labels, created_functions))
        if skipped_not_in_memory > 0:
            print("因地址不在当前程序内存而跳过: %d 条（请检查 ADDRESS_OFFSET，见脚本顶部）" % skipped_not_in_memory)
        if skipped_bad_name > 0:
            print("因名称为空或无效而跳过: %d 条" % skipped_bad_name)
        if created_labels == 0 and skipped_not_in_memory > 0:
            print("")
            print("提示: 若符号文件中的地址与 Ghidra 加载基址不一致，请在脚本顶部设置 ADDRESS_OFFSET。")
            print("  例如 Ghidra 中程序起始于 0x%x，符号最小地址 0x%x，可设 ADDRESS_OFFSET = 0x%x" % (
                prog_min, sym_min, (prog_min - sym_min) if sym_min != prog_min else 0))
        print("建议: 菜单 Analysis -> Auto Analyze 或 重新分析，以更新反编译与函数边界。")
