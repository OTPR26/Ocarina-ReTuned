#!/usr/bin/env python3
"""Support the status-register restore used by the randomizer ABI wrappers."""
import argparse
from pathlib import Path
from apply_host_services import replace

def apply(engine):
    path=engine/'tools/oot3d/native_a32_runtime/whole_aot_cpp.py'
    text=path.read_text()
    text=replace(text,'        if fields != 0x8:', '        if fields not in (0x8, 0xC):')
    text=replace(text,'                "state.SetPreservedCpsrBits(0xFF000000U, value);",',
        '                f"state.SetPreservedCpsrBits(0x{0xFF0F0000 if fields == 0xC else 0xFF000000:08X}U, value);",')
    text=replace(text,'        0x0E200B00,','        0x0E100B00,\n        0x0E100B40,\n        0x0E200B40,\n        0x0E200B00,')
    path.write_text(text)
    path=engine/'tools/oot3d/native_a32_runtime/upstream/recomp/a32_vfp_binary64.cpp'
    text=path.read_text()
    anchor='    case 0x0E200B00U:\n    case 0x0E300B00U:'
    text=replace(text,anchor,'    case 0x0E100B00U:\n    case 0x0E100B40U:\n    case 0x0E200B40U:\n'+anchor)
    anchor='    case 0x0E200B00U:\n        result = F64Mul'
    text=replace(text,anchor,'''    // ARM VNMLS/VNMLA round the product before adding the negated accumulator.
    case 0x0E100B00U:
    case 0x0E100B40U: {
        const auto product = F64Mul(ReadDouble(state, left), ReadDouble(state, right), control);
        const auto negateProduct = (raw & kTernaryMask) == 0x0E100B40U;
        result = F64Add(ReadDouble(state, destination) ^ kSignBit64,
                        product.value ^ (negateProduct ? kSignBit64 : 0U), control);
        result.flags |= product.flags;
        break;
    }
    case 0x0E200B40U:
        result = F64Mul(ReadDouble(state, left), ReadDouble(state, right), control);
        result.value ^= kSignBit64;
        break;
''' + anchor)
    path.write_text(text)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('engine',type=Path);apply(p.parse_args().engine)
