# Polorsk V228 vs official Fosi V1.5.5: cover artwork

**Status:** Static binary comparison. No Polorsk image has been modified; no on-device tests were performed as part of this comparison.

## Sources
- Official `DP3_V155.img` SHA-256: `4713a2eb4b523d49ad003ac2df159c1c596339aef1a9a060e6ea6bbbf18e1332`.
- Polorsk `DP3_V228.img` SHA-256: `1ac1a5d2886e12eaa9b391ae0e987ae392d306855d3ca02f36b205d647a74d4b`.
- Both are 13,631,492 bytes, firmware payload ends at 0xCB0000, 82 module-table entries, validated CRC/header.
- User reports Polorsk omits covers larger than 144 pixels. This is a **user-observed threshold**, not yet a proven input-validation condition.

## Findings

### Polorsk introduces a dedicated Cover Flow/cache implementation
Module **30** is significantly rewritten:
- V155: 8,304-byte code region at file offset `0x8C200`.
- Polorsk: 5,584-byte code region at the **same file offset**; 5,504 bytes differ in the common span.
- Polorsk contains these readable, image-related literals within module 30:
  - `Building Cover Flow` at image offset `0x8D701`
  - `Cover Flow` at `0x8D73F`
  - `no artwork` at `0x8D72C`
  - `CFCACHE.BIN` at `0x8D672` (also elsewhere)
  - `CFCACHE BIN` at `0x8D74A`
  - `no albums in the music library` at `0x8D653`
  - `card must be FAT32 or exFAT`, `card write failed`, and `delete CFCACHE.BIN on the card`
- None of those exact Cover Flow/cache strings occur anywhere in the official V155 binary. This strongly points to **Polorsk-specific Cover Flow cache generation**.

### A 144 value is embedded in Polorsk's new module
- Polorsk module 30 contains little-endian halfwords `0x0090, 0x0090` (144, 144), starting at module-relative `0x15BC`, image offset `0x8D7BC`.
- It also contains several Thumb `movs ..., #144`-like encodings, whereas the official module 30 has none at those positions.
- This is **consistent with** a 144x144 image or UI/cache geometry, but does **not prove** that artwork with a larger original JPEG/PNG resolution is rejected. Such values could instead describe display dimensions, buffer geometry, or a thumbnail output size.
- The actual input-image rejection branch, JPEG decoder limitations, image memory allocation, or cache workflow must be identified before patching.

### Broader binary differences
- Across V155 and V228: 1,093,309 bytes differ in matching file positions, including resource sections. Total byte difference is **not a measure of changed code or of artwork handling**.
- Polorsk changes module 0 (3,139 bytes different), and changes modules 18, 21, 23, 27, 30, 32, 38, 39 among others.
- Resource-section changes also occur, but do not by themselves establish an image decoder limit.

### NeoPod comparison
- NeoPod's `src/library/cover_build.c` calls `cover_image_decode()` to decode source artwork into full/half-sized cached pixel arrays.
- NeoPod's cover flow renders these cached images. This is a separate artwork pipeline from Polorsk's `CFCACHE.BIN` mechanism.
- NeoPod code should **not** be copied bytewise into stock/Polorsk firmware: the binary interfaces, memory budget, and cache formats differ.

## Next validation steps

1. Duplicate one known-working FLAC with a **144x144 JPEG** cover and another with **145x145 JPEG** cover, same JPEG format, similar compression/metadata, and identical audio; determine if there is a true threshold. Include 256x256 and 500x500 controls.
2. Delete/rebuild Polorsk's `CFCACHE.BIN` between tests **only after backing up the card**, following the firmware's documented cache workflow.
3. Determine whether the threshold is a strict dimension check, an image byte-size limit, JPEG format compatibility, or cache decoding/memory failure.
4. Reverse-engineer the module 30 path around the JPEG loader and output-cache writer before any patch.
5. Do not flash experimental binary changes without a verified patch scope and a recovery path.

**No code changes were made as part of this analysis.** All evidence above is static, not a runtime trace.
