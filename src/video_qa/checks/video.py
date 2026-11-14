from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ffmpeg_utils import ffmpeg_filter_log, find_floats
from ..models import FAIL, PASS, CheckResult


def check_black_frames(path: Path, spec: dict[str, Any]) -> CheckResult:
    v = spec["video"]
    log = ffmpeg_filter_log(
        path, vf=f"blackdetect=d={v['black_min_duration_s']}:pix_th={v['black_pixel_threshold']}")
    durations = find_floats(r"black_duration:([\d.]+)", log)
    starts = find_floats(r"black_start:([\d.]+)", log)
    if durations:
        segs = [{"start": s, "duration": d} for s, d in zip(starts, durations)]
        return CheckResult("black_frames", FAIL,
                           f"Nalezeno {len(segs)} černých úseků (první v {segs[0]['start']:.1f} s)",
                           {"segments": segs})
    return CheckResult("black_frames", PASS, "žádné černé úseky")


def check_freeze(path: Path, spec: dict[str, Any]) -> CheckResult:
    v = spec["video"]
    log = ffmpeg_filter_log(
        path, vf=f"freezedetect=n={v['freeze_noise_db']}dB:d={v['max_freeze_s']}")
    starts = find_floats(r"freeze_start: ([\d.]+)", log)
    durations = find_floats(r"freeze_duration: ([\d.]+)", log)
    if starts:
        segs = [{"start": s, "duration": d} for s, d in zip(starts, durations)] or [
            {"start": s, "duration": None} for s in starts]
        return CheckResult("frozen_video", FAIL,
                           f"Zamrzlý obraz > {v['max_freeze_s']} s v {segs[0]['start']:.1f} s",
                           {"segments": segs})
    return CheckResult("frozen_video", PASS, f"žádné zamrznutí > {v['max_freeze_s']} s")

