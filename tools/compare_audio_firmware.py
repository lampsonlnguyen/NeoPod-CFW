#!/usr/bin/env python3
"""Read-only comparison of stock V137, stock V155, and Polorsk V228.

No firmware is modified or repackaged. Run from the repository root:
  python tools/compare_audio_firmware.py
  python tools/compare_audio_firmware.py --json build/audio-reference-comparison.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "third_party" / "nanitecfw"))
from rknano_fw import Image  # noqa: E402

DEFAULTS = {
    "V137": ROOT / "assets" / "DP3_V137.img",
    "V155": ROOT / "assets" / "DP3_V155.img",
    "V228": ROOT / "DP3_V228.img",
}
# V228 offsets were verified on the exact reference image, not on V155/V137.
V228_SHA256 = "1ac1a5d2886e12eaa9b391ae0e987ae392d306855d3ca02f36b205d647a74d4b"
CLOCK_WORDS = {
    "I2S 96k register": 0x00033F3F,
    "I2S 192k register": 0x00013F3F,
    "I2S 48k register": 0x00073F3F,
    "I2S0 peripheral base": 0x40020000,
    "I2S1 peripheral base": 0x40030000,
}
RATES = (44100, 48000, 88200, 96000, 176400, 192000)
KEY_REGIONS_V228 = [
    ("sample-rate clock selection", 0x29E56, 0x29F9A),
    ("ACODEC table selection and writes", 0x2AC66, 0x2AD10),
    ("I2S initialization", 0x2A150, 0x2A1B0),
    ("ACODEC rate table (selector 2)", 0x479BC, 0x47A4C),
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def word_offsets(data, word, limit=30):
    needle = struct.pack("<I", word)
    found = []
    pos = -1
    while len(found) < limit:
        pos = data.find(needle, pos + 1)
        if pos < 0:
            break
        if pos % 4 == 0:
            found.append(f"0x{pos:X}")
    return found


def structure(image):
    return {
        "load_base": f"0x{image.load_base:08X}",
        "build_date": image.date,
        "fw_len": f"0x{image.fw_len:X}",
        "header_copy_ok": image.header_copy_ok(),
        "crc_ok": image.crc_stored() == image.crc_calc(),
        "modules": [
            {key: (f"0x{value:08X}" if key.endswith(("_load", "_exec")) else value)
             for key, value in mod.items()}
            for mod in image.modules
        ],
    }


def slices_for_image(image):
    spans = {}
    for m in image.modules:
        for kind in ("code", "data"):
            length = m[kind + "_len"]
            if not length:
                continue
            offset = image.l2f(m[kind + "_load"])
            if offset < 0 or offset + length > len(image.d):
                raise ValueError(f"Module {m['index']} {kind} exceeds file bounds")
            spans[f"module{m['index']}_{kind}"] = (offset, length)
    for section in image.sections:
        offset, length = section["offset"], section["length"]
        if length <= 0 or offset < 0 or offset + length > len(image.d):
            continue
        spans["section_" + section["name"]] = (offset, length)
    return spans


def diff_runs(a, b, limit=12):
    # Compare common lengths and describe changed spans without copying binary data.
    runs = []
    start = None
    total = 0
    for idx in range(min(len(a), len(b))):
        changed = a[idx] != b[idx]
        if changed:
            total += 1
            if start is None:
                start = idx
        elif start is not None:
            if len(runs) < limit:
                runs.append([f"0x{start:X}", f"0x{idx:X}"])
            start = None
    if start is not None and len(runs) < limit:
        runs.append([f"0x{start:X}", f"0x{min(len(a),len(b)):X}"])
    return {"different_bytes_in_overlap": total, "first_changed_runs": runs,
            "size_delta": len(b) - len(a)}


def compare_images(name_a, a, name_b, b, meta_a, meta_b):
    spans_a = slices_for_image(meta_a)
    spans_b = slices_for_image(meta_b)
    rows = []
    for key in sorted(set(spans_a) | set(spans_b)):
        sa, sb = spans_a.get(key), spans_b.get(key)
        if sa is None or sb is None:
            rows.append({"region": key, "status": "missing in one image"})
            continue
        start_a, length_a = sa
        start_b, length_b = sb
        block_a = a[start_a:start_a + length_a]
        block_b = b[start_b:start_b + length_b]
        rows.append({
            "region": key,
            "file_offset_a": f"0x{start_a:X}",
            "file_offset_b": f"0x{start_b:X}",
            "bytes_a": length_a,
            "bytes_b": length_b,
            "identical": block_a == block_b,
            "sha256_a": sha256(block_a),
            "sha256_b": sha256(block_b),
        })
    return {"pair": f"{name_a} vs {name_b}", "byte_diff": diff_runs(a, b),
            "regions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for label in DEFAULTS:
        parser.add_argument("--" + label.lower(), type=Path, default=DEFAULTS[label])
    parser.add_argument("--json", type=Path, help="Optional JSON report output (not firmware)")
    args = parser.parse_args()
    paths = {label: getattr(args, label.lower()) for label in DEFAULTS}
    images = {}
    metadata = {}
    report = {"firmware": {}, "comparisons": [], "v228_checked_regions": []}

    for label, path in paths.items():
        if not path.is_file():
            parser.error(f"{label} not found: {path}")
        data = path.read_bytes()
        img = Image(data)
        digest = sha256(data)
        if not img.header_copy_ok() or img.crc_stored() != img.crc_calc():
            raise SystemExit(f"{label}: invalid header copy or firmware CRC: {path}")
        images[label], metadata[label] = data, img
        info = structure(img)
        info.update({"path": str(path), "bytes": len(data), "sha256": digest})
        info["audio_constants"] = {
            title: word_offsets(data, value) for title, value in CLOCK_WORDS.items()
        }
        info["sample_rate_literals"] = {
            str(rate): word_offsets(data, rate, limit=15) for rate in RATES
        }
        report["firmware"][label] = info

    for left, right in (("V137", "V155"), ("V155", "V228"), ("V137", "V228")):
        report["comparisons"].append(compare_images(
            left, images[left], right, images[right], metadata[left], metadata[right]))

    if report["firmware"]["V228"]["sha256"] == V228_SHA256:
        data = images["V228"]
        for title, begin, end in KEY_REGIONS_V228:
            needle = data[begin:end]
            row = {"name": title, "v228_offset": f"0x{begin:X}",
                   "bytes": len(needle), "sha256": sha256(needle)}
            for label in ("V137", "V155"):
                offset = images[label].find(needle)
                row[label + "_exact_match_offset"] = None if offset < 0 else f"0x{offset:X}"
            report["v228_checked_regions"].append(row)
    else:
        report["warning"] = "V228 SHA differs from verified reference; known offsets intentionally skipped"

    for label, info in report["firmware"].items():
        print(f"{label}: {info['bytes']:,} bytes SHA256={info['sha256']}")
        print(f"  build={info['build_date']} header_copy={info['header_copy_ok']} "
              f"crc={info['crc_ok']} modules={len(info['modules'])}")
        print(f"  192k I2S constant locations: "
              f"{', '.join(info['audio_constants']['I2S 192k register'][:8]) or '(none)'}")

    for comparison in report["comparisons"]:
        row = comparison["byte_diff"]
        altered = [x["region"] for x in comparison["regions"] if x.get("identical") is False]
        print(f"\n{comparison['pair']}: changed bytes in overlap "
              f"{row['different_bytes_in_overlap']:,}; length delta {row['size_delta']:+,}")
        print("  changed regions: " + (", ".join(altered) or "(none)"))
        print("  first changed file spans: " + str(row["first_changed_runs"][:6]))

    print("\nV228 identified clock/audio regions (exact byte matches only):")
    for row in report["v228_checked_regions"]:
        print(f"  {row['name']}: V137={row['V137_exact_match_offset']} "
              f"V155={row['V155_exact_match_offset']}")

    print("\nNOTE: Identical byte patterns do not prove runtime execution. "
          "Different byte patterns do not identify root cause.")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"JSON report: {args.json}")


if __name__ == "__main__":
    main()
