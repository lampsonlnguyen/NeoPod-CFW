# Fosi / Polorsk audio firmware comparison (sandbox)

## Provenance

- `assets/DP3_V137.img`: stock Fosi V1.3.7; current build template.
- `assets/DP3_V155.img`: user-uploaded official Fosi V1.5.5.
- `DP3_V228.img`: Polorsk custom V228 **based on official V1.5.5** (not official Fosi V2.2.8).
- V1.5.5 release notes explicitly mention improved FLAC format compatibility and power-saving mode, but do **not** claim a 192 kHz playback fix.

## What we have verified

Disassembly and direct table extraction from all three supplied images established these **distinct** rate configurations:

| Rate | I2S_CKR | ACODEC M4 | M5 | M6 | M7 field |
| --- | --- | --- | --- | --- | --- |
| 96 kHz | `0x00033F3F` | `0x00` | `0x30` | `0x19` | `0x09` |
| 192 kHz | `0x00013F3F` | `0x04` | `0x49` | `0x19` | `0x03` |

The V228 selection function at image offset `0x29E56` selects table 2/index 3 for 96 kHz and table 1/index 4 for 192 kHz. The indexed table rows are identical in stock V137, official V155 and Polorsk V228. For V155/V228, the 96 kHz row begins at file offset `0x47A04` and the 192 kHz row at `0x47AAC`. V137 rows begin at `0x476E8` and `0x47790` respectively. Table entries have 24-byte stride; the last four little-endian words specify the ACODEC register values.

NeoPod's prior `dac.c` incorrectly reused the 96 kHz ACODEC row at 192 kHz. We changed only the 192 kHz ACODEC row to `04/49/19/03` on `sandbox`, leaving I2S and DMA unchanged. This is a source-level correction, **not a hardware-verified playback fix**.

User device tests: 192 kHz WAV and FLAC are both slow, while 96 kHz FLAC works. This is evidence against a *FLAC decoder-only* explanation. DMA ring-wrap accounting has not yet been established; the apparent playback throughput in previous pause logs is not a trustworthy sample-clock measurement.

## Run read-only comparison locally

```powershell
cd C:\github\NeoPod-CFW
git switch sandbox
git pull origin sandbox
python .\tools\compare_audio_firmware.py --json .\build\audio-reference-comparison.json
```

The tool checks image header copies and CRC, compares modules by module-defined regions, lists 96/192 kHz clock constants, and searches for **exact copies** of V228 reference clock/ACODEC routines in V137 and V155. The report includes SHA-256 digests and offset-based differences, not proprietary binary contents. No images are modified.

**Interpretation:** Exact match is strong evidence for unchanged bytes; absence of an exact match does not imply an entirely different clock behavior. Differences in module layouts can shift file offsets. Do not assume that raw image offsets are runtime addresses or that static reference routines necessarily execute.

## Recommended sequence

1. Review the generated `build/audio-reference-comparison.json` and identify altered audio-related modules.
2. Compare the *same runtime functions* across images using mapped module code offsets, not a raw offset-for-offset dump.
3. Inspect CRU clock source/divider setup and DMA timing, in addition to ACODEC and I2S registers.
4. Implement any proven difference as a small, open-source, hardware-specific patch protected by a switch; test 96 kHz and 192 kHz WAV before FLAC.
5. Leave `assets/DP3_V137.img` as the build template until compatibility and licensing issues are resolved. No proprietary binary should be copied into NeoPod source code.

