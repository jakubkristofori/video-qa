from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..ffmpeg_utils import duration, ffmpeg_filter_log, find_floats
from ..models import FAIL, PASS, SKIP, CheckResult


def check_loudness(path: Path, spec: dict[str, Any]) -> list[CheckResult]:
    a = spec["audio"]
    log = ffmpeg_filter_log(path, af="loudnorm=print_format=json")
    blocks = re.findall(r"\{[^{}]*\}", log, flags=re.DOTALL)
    if not blocks:
        return [CheckResult("loudness", FAIL, "ffmpeg nevrátil data o hlasitosti")]
    data = json.loads(blocks[-1])
    lufs, tp = float(data["input_i"]), float(data["input_tp"])
    ok_l = abs(lufs - a["target_lufs"]) <= a["lufs_tolerance"]
    ok_p = tp <= a["max_true_peak_db"]
    return [
        CheckResult("loudness", PASS if ok_l else FAIL,
                    f"{lufs:.1f} LUFS" if ok_l else
                    f"{lufs:.1f} LUFS, cíl {a['target_lufs']} ±{a['lufs_tolerance']}",
                    {"lufs": lufs}),
        CheckResult("true_peak", PASS if ok_p else FAIL,
                    f"{tp:.1f} dBTP" if ok_p else f"{tp:.1f} dBTP > {a['max_true_peak_db']} (klipování)",
                    {"true_peak_db": tp}),
    ]


def check_silence_edges(path: Path, probe: dict[str, Any], spec: dict[str, Any]) -> list[CheckResult]:
    a = spec["audio"]
    total = duration(probe)
    log = ffmpeg_filter_log(
        path, af=f"silencedetect=n={a['silence_threshold_db']}dB:d=0.3")
    starts = find_floats(r"silence_start: (-?[\d.]+)", log)
    ends = find_floats(r"silence_end: (-?[\d.]+)", log)

    # ffmpeg na konci souboru vypíše silence_end == délka, proto porovnáváme s tolerancí.
    leading = 0.0
    if starts and starts[0] <= 0.05:
        leading = ends[0] if ends else total
    trailing = 0.0
    if starts and (len(starts) > len(ends) or ends[-1] >= total - 0.15):
        trailing = total - starts[-1]

    def edge(name: str, label: str, seconds: float, limit: float) -> CheckResult:
        ok = seconds <= limit
        msg = f"{seconds:.2f} s" if ok else f"{label} {seconds:.2f} s > {limit} s"
        return CheckResult(name, PASS if ok else FAIL, msg, {"seconds": seconds})

    return [
        edge("leading_silence", "Ticho na začátku", leading, a["max_leading_silence_s"]),
        edge("trailing_silence", "Ticho na konci", trailing, a["max_trailing_silence_s"]),
    ]


def skip_audio(reason: str) -> list[CheckResult]:
    return [CheckResult("audio_checks", SKIP, reason)]
