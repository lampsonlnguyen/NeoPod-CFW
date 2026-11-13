# Wired FLAC battery benchmark

This experiment adds **optional** telemetry for the Fosi DAP Neo. It does not adjust processor clocks or audio behavior.

## Build

Configure the Neo device build with:

```powershell
cmake -S . -B build/neo -DECHO_BATTERY_BENCHMARK=ON
powershell -NoProfile -ExecutionPolicy Bypass -File .\build-neopod.ps1
```

The build script may configure a different build directory or override options; check `build/neo/CMakeCache.txt` for `ECHO_BATTERY_BENCHMARK:BOOL=ON` and confirm the compiled image was rebuilt. This switch is OFF by default and active only for `ECHO_BOARD=neo`. Reconfigure with `-DECHO_BATTERY_BENCHMARK=OFF` to remove instrumentation.

## Test conditions

- Charge to 100%, unplug USB, then start the same repeat-enabled FLAC playlist.
- Wired 3.5 mm headphones, same volume and gain, Bluetooth off, EQ off, ReplayGain off.
- Let the display turn off. Do not interact with the player during the run.
- Leave device at the same room temperature and use the same MicroSD card.
- Shut down **normally** near 20% battery so results are written to the card; don't drain to an abrupt power cut.
- Save `/.echo/battery-bench.csv` to your PC after each run before starting another test.
- Run the original and optimized builds at least three times each.

## Recorded columns

`elapsed_s,battery_mv,battery_pct,cpu_mhz,underruns,output_underruns`

One sample is taken on entering screen-off FLAC playback and every 10 minutes thereafter. A final sample is attempted on orderly shutdown. 144 samples accommodate approximately 24 hours. Data are buffered in RAM to avoid continuous SD writes. The file is overwritten on successful shutdown.

**Limits:** Logging only occurs when playing audio, screen is dark, and USB power is absent. The counter is cumulative and may include underruns outside the measured interval; compare first and last values. Battery percentage is approximate. If playback pauses or screen wakes, the recorder skips samples (elapsed time still advances). On a sudden reset or battery power loss, RAM samples are lost. A single CSV does not prove that the workload was exclusively FLAC; keep playback conditions fixed.

## Analyze

```powershell
python tools/battery_benchmark_report.py baseline1.csv optimized1.csv
```

The report estimates elapsed time between the 90% and 30% thresholds when both thresholds are covered, and shows the underrun changes. Compare median runtime over three independent runs per version.

## Safety

This is an **uncompiled first-pass** source change. Build it, confirm the CSV is valid, and test on the device before using its measurements for optimization decisions. Reflash only with a known-good recovery route.
