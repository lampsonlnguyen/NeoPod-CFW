#!/usr/bin/env python3
"""Summarize battery benchmark CSV data (standard library only)."""
import argparse
import csv
from pathlib import Path


def load(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    required = ("elapsed_s", "battery_mv", "battery_pct", "cpu_mhz",
                "underruns", "output_underruns")
    if any(key not in rows[0] for key in required):
        raise ValueError(f"{path}: missing required columns")
    values = [{key: int(row[key]) for key in required} for row in rows]
    if any(b["elapsed_s"] < a["elapsed_s"] for a, b in zip(values, values[1:])):
        raise ValueError(f"{path}: elapsed times not sorted")
    return values


def crossing(rows, threshold):
    for first, second in zip(rows, rows[1:]):
        a, b = first["battery_pct"], second["battery_pct"]
        if a >= threshold >= b:
            if a == b:
                return float(first["elapsed_s"])
            fraction = (a - threshold) / (a - b)
            return first["elapsed_s"] + fraction * (
                second["elapsed_s"] - first["elapsed_s"])
    return None


def summarize(path):
    rows = load(path)
    t90, t30 = crossing(rows, 90), crossing(rows, 30)
    measured = None if t90 is None or t30 is None or t30 < t90 else (t30 - t90) / 3600
    print(f"\n{path}: {len(rows)} samples")
    print(f"  Window: {rows[0]['elapsed_s']/3600:.2f}–{rows[-1]['elapsed_s']/3600:.2f} h")
    print(f"  Battery: {rows[0]['battery_pct']}% -> {rows[-1]['battery_pct']}%")
    print(f"  Voltage: {rows[0]['battery_mv']} -> {rows[-1]['battery_mv']} mV")
    print(f"  Clock frequencies: {sorted({row['cpu_mhz'] for row in rows})} MHz")
    print(f"  Underrun increase: {rows[-1]['underruns']-rows[0]['underruns']}")
    print(f"  Output underrun increase: {rows[-1]['output_underruns']-rows[0]['output_underruns']}")
    print(f"  90% to 30% runtime: {measured:.2f} h" if measured is not None
          else "  90% to 30% runtime: unavailable (thresholds not covered)")
    return measured


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+", help="Battery log CSV files")
    args = parser.parse_args()
    periods = [summarize(path) for path in args.csv]
    if len(periods) == 2 and all(p is not None and p > 0 for p in periods):
        print(f"\nChange (second versus first): {(periods[1]/periods[0]-1)*100:+.1f}%")


if __name__ == "__main__":
    main()
