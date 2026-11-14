# NeoPod: reproducible 192 kHz reverse-engineering notes

## Objective
Build an independently maintainable, openly documented implementation for Fosi DAP Neo rather than relying on another developer's opaque precompiled CFW. Begin with verified 192 kHz audio behavior. This is a research notebook, not a tested firmware fix.

## Reference image
- Input: user-provided `DP3_V228.img`
- Size: **13,631,492 bytes**
- SHA-256: `1ac1a5d2886e12eaa9b391ae0e987ae392d306855d3ca02f36b205d647a74d4b`
- Image header includes `Rockchip` and `RKnano SDK 1.0`.
- No source or build provenance for the image has been established. Treat it as a compiled *reference*, not redistributable open-source code.

## Verified static observations

The following 32-bit little-endian words occur contiguously near code-looking bytes in the uploaded image:

| File offset | Value | Possible role |
|---|---|---|
| `0x2A114` | `0x00033F3F` | I2S clock register constant |
| `0x2A118` | `0x00073F3F` | I2S clock register constant |
| `0x2A120` | `0x00013F3F` | I2S clock register constant |

The image also contains little-endian integers for 96,000 and 192,000 Hz, including 192,000 at `0xEA658`, `0xEA6A4`, `0xEA6E4`, and `0xEA724`. Seeing these bytes does **not** establish the rate-selection path, DAC setup sequence, or that 192 kHz plays correctly in the reference firmware.

At `0x2A10C` and `0x2A110`, 32-bit words read `0x40020000` and `0x40030000`, respectively. NeoPod uses `0x40030000` as its I2S1 peripheral base; this makes the local code/data region worth disassembling. Those addresses are *not* proof of a particular executing instruction.

## NeoPod open-source implementation

- `platform/device/board/dac.c` declares I2S1 base `0x40030000` and I2S_CKR `+0x08`.
- `platform/device/logic/audio_math.c` computes `(mclk + 32*rate)/(64*rate) - 1` using integer rounding; at 24.576 MHz / 192 kHz, divider = 1 and I2S_CKR = `0x00013F3F`.
- For 96 kHz with the same mclk, divider = 3 and I2S_CKR = `0x00033F3F`.
- `platform/device/board/dac.c` sets CRU I2S source, divider, output and clock, then I2S_CKR. The *actual resulting master-clock frequency* has not been measured.

## Hardware test evidence from user

- 24-bit / 96 kHz FLAC: normal playback.
- 24-bit / 192 kHz FLAC: slow playback.
- 24-bit / 192 kHz WAV: also slow.
- 192 kHz diagnostics: requested DAC rate 192000, I2S_CKR readback 81727 (`0x00013F3F`), Core 1 FLAC active for FLAC, 3 engine underruns, 0 hardware-output underruns.
- These observations favor a **common 192 kHz output path issue** over a FLAC-only issue. They do not yet establish whether the output master clock, I2S frame timing, DMA counter/wrap handling, or other 192 kHz setup is responsible.

## Next experiments (no blind register changes)

1. Record both 96 kHz and 192 kHz **WAV** snapshots with effective DMA consumption and elapsed time; use sufficiently frequent sampling to avoid circular ring-wrap ambiguity.
2. Capture the CRU clock mux/divider register readbacks in addition to I2S_CKR and the ACODEC setup registers at each sample rate.
3. Trace ARM/Thumb code references to the three literals near file offset `0x2A114` using Ghidra, starting from the appropriate decoded firmware module / load address. The raw image file offset is not automatically the code's runtime address.
4. Identify the 192 kHz initialization branch and document its complete ordered register-write sequence; compare against `platform/device/board/dac.c`.
5. Make a minimal device-only change protected by a feature flag, keeping the existing 96 kHz route unchanged. Build and test, then capture logs.
6. Convert validated findings into well-named registers, unit tests, architecture documentation and an independently authored permissively licensed implementation. Do not copy unlicensed original firmware code into the repository.

## Reproduction

```
python analyze_neopod_reference.py DP3_V228.img
```

The script uses only Python's standard library and does not modify either the input image or device.
