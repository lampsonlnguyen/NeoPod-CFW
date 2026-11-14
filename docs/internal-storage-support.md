# Internal storage on Fosi DAP Neo — implementation status

**Status: NOT SUPPORTED by NeoPod on hardware yet. Do not label this as working.**

## Verified in sandbox source

- `platform/device/board/storage.c` mounts a single `FatVolume` using `sd_start()`. All `hal_file_*` and `hal_dir_*` functions use that MicroSD volume.
- `platform/device/board/emmc.c` has an explicit `#ifdef ECHO_BOARD_NEO` early return in `emmc_start()`, because eMMC controller/pinmux initialization has not been validated for this board.
- On Neo, `emmc_write()` intentionally returns false. **Keep this safety guarantee** until hardware and partition boundaries are verified.
- `src/app/app_screens.c` has one indexed library and a single `Folders` entry. `src/app/browse_screen.c` browses that library, rather than a drive-level filesystem chooser.
- Building with V155 as the packaging template does not automatically enable eMMC support because NeoPod overwrites the primary application module.

## Safe acceptance criteria

1. Identify the correct Neo eMMC hardware controller and pinmux from stock V155, **without writing to flash**. Confirm the initialization sequence does not conflict with MicroSD, USB, or recovery.
2. Add a board-specific **read-only** eMMC mount and validate `emmc_layout_read()` against actual device sector counts. Do not scan/write firmware partitions as user media.
3. Refactor `storage.c` to track separate MicroSD and internal `FatVolume` instances and isolate open-file and open-directory handles by drive. Keep SD default paths backward-compatible (`/.echo/...` and existing music files).
4. Provide a read-only drive chooser (e.g. `MicroSD Card` / `Internal Storage`) only for volumes that actually mounted. Never show a nonfunctional drive as though it were usable.
5. Decide how to incorporate internal music into the library: index each volume separately or add storage identity to track paths. Player, artwork, playlists, scan and saved settings must resolve the same volume reliably.
6. Validate on an eMMC **read-only** test image and then on actual Neo hardware, including no-card boot, eject/reinsert, both volumes present, failed internal mount, and repeated reboot.
7. Require a successful hardware test before claiming the feature works or enabling any internal write/USB Mass Storage exposure.

## Non-goals / safeguards

- **Do not remove the `ECHO_BOARD_NEO` eMMC guard just to make Internal Storage appear.**
- Do not treat the Fosi V155 update image as a source of working eMMC driver code: the full image is a template, not an executed driver.
- Do not touch boot firmware slots or expose raw eMMC partitions as storage.
- Leave normal MicroSD playback and the existing sandbox build operational until dual-volume playback is verified.
