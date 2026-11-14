"""Read-only verification of V228 reference ACODEC rate tables.

Usage: python verify_neopod_acodec_tables.py DP3_V228.img
SHA256 expected: 1ac1a5d2886e12eaa9b391ae0e987ae392d306855d3ca02f36b205d647a74d4b

These offsets are specific to the supplied V228 firmware image and must not
be generalized to other versions. This tool does NOT modify firmware.
"""
from pathlib import Path
import hashlib
import struct
import sys

EXPECTED_SHA = '1ac1a5d2886e12eaa9b391ae0e987ae392d306855d3ca02f36b205d647a74d4b'
TABLES = {0: (0x2B054, 0x47ADC), 1: (0x2B058, 0x47A4C), 2: (0x2B05C, 0x479BC)}

def read_word(data, offset):
    return struct.unpack_from('<I', data, offset)[0]

def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python verify_neopod_acodec_tables.py DP3_V228.img')
    data = Path(sys.argv[1]).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    print('SHA256:', digest)
    if digest != EXPECTED_SHA:
        raise SystemExit('This is not the exact reference image analyzed; refusing unverified offsets.')
    mapping = None
    for selector, (literal_offset, file_start) in TABLES.items():
        address = read_word(data, literal_offset)
        candidate = address - file_start
        if mapping is None:
            mapping = candidate
        if candidate != mapping:
            raise SystemExit('Reference file/runtime mapping is inconsistent.')
        print(f'Selector {selector}: runtime=0x{address:08X} file=0x{file_start:X}')
    print(f'Runtime address = file offset + 0x{mapping:08X} (for these tables)')

    # At 0x29EF4, Thumb 16-bit B<cond> uses signed imm8 in halfwords.
    branch_at = 0x29EF4
    halfword = struct.unpack_from('<H', data, branch_at)[0]
    if (halfword & 0xFF00) != 0xD000:
        raise SystemExit('Unexpected 192kHz branch instruction.')
    delta = (halfword & 0xFF) << 1
    if delta >= 256:
        delta -= 512
    target = branch_at + 4 + delta
    print(f'192kHz branch at 0x{branch_at:X}: 0x{halfword:04X} -> 0x{target:X}')
    if target != 0x29F0A:
        raise SystemExit('Unexpected 192kHz branch target.')

    # From the supplied Thumb disassembly: 96kHz: r4 starts at 0 and branches
    # to 0x29F0A (three increments); 192kHz: r4 set to 1 at 0x29EF2,
    # then branches to 0x29F0A (three increments). Both use selector 2.
    for rate, index in ((96000, 3), (192000, 4)):
        off = TABLES[2][1] + 24 * index
        entry = struct.unpack_from('<6I', data, off)
        # Reference routine loads (r6,r5,ip,r3) from entry offsets +8..+20.
        fields = entry[2:]
        print(f'{rate} Hz: table=2 index={index} file=0x{off:X} '
              f'ACODEC M4/M5/M6/M7-field={tuple(hex(x) for x in fields)}')
        assert fields == (0x00, 0x30, 0x19, 0x09), (rate, fields)
    print('PASS: 96kHz and 192kHz ACODEC fields match NeoPod RATES[].')
    print('No firmware changes are proposed by this script.')

if __name__ == '__main__':
    main()
