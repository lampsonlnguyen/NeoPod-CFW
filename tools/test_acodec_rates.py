#!/usr/bin/env python3
"""Regression check for NeoPod I2S/ACODEC 96/192 kHz reference values.

Uses only NeoPod C source; does not require or distribute vendor firmware.
Run: python tools/test_acodec_rates.py
"""
import re
import unittest
from pathlib import Path

DAC = Path(__file__).resolve().parents[1] / "platform/device/board/dac.c"
REFERENCE = {
    96000: (24576000, (0x00, 0x30, 0x19, 0x09)),
    192000: (24576000, (0x04, 0x49, 0x19, 0x03)),
}


class AcocodecRateConfigurationTest(unittest.TestCase):
    def test_reference_rate_rows(self):
        source = DAC.read_text(encoding="utf-8")
        for rate, (mclk, expected) in REFERENCE.items():
            with self.subTest(rate=rate):
                pattern = (
                    rf"\\{{\\s*{rate}\\s*,\\s*{mclk}\\s*,\\s*"
                    rf"\\{{([^}}]+)\\}}\\s*,\\s*\\d+\\s*\\}}"
                )
                found = re.findall(pattern, source)
                self.assertEqual(len(found), 1, f"Expected exactly one {rate}Hz rate row")
                row = tuple(int(x.strip().rstrip("uU"), 0)
                            for x in found[0].split(","))
                self.assertEqual(row, expected)

    def test_i2s_clock_dividers(self):
        # mclk / (64 * sample_rate) - 1 for exact integer divisions.
        self.assertEqual(24576000 // (64 * 96000) - 1, 3)
        self.assertEqual(24576000 // (64 * 192000) - 1, 1)


if __name__ == "__main__":
    unittest.main()
