# Fosi / Polorsk audio firmware comparison (sandbox)

## Provenance

- `assets/DP3_V137.img`: stock Fosi V1.3.7; current build template.
- `assets/DP3_V155.img`: user-uploaded official Fosi V1.5.5.
- `DP3_V228.img`: Polorsk custom V228 **based on official V1.5.5** (not official Fosi V2.2.8).
- V1.5.5 release notes explicitly mention improved FLAC format compatibility and power-saving mode, but do **not** claim a 192 kHz playback fix.

## What we have verified

The V228 Thumb disassembly selects different sample-rate table indices, but the verified V228 rate entries for **96 kHz and 192 kHz** both use `ACODEC_M4/M5/M6/M7 = 00/30/19/09`. The I2S clock register values are `0x00033F3F` (96 kHz) and `0x00013F3F` (192 kHz). These agree with NeoPod's current values. Thus changing those constants without more evidence is **not** justified.

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

