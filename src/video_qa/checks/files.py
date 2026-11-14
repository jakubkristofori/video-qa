from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ffmpeg_utils import ToolError, ffprobe
from ..models import FAIL, PASS, CheckResult


def check_required_files(base: Path, files: dict[str, str]) -> list[CheckResult]:
    results = []
    for key, rel in files.items():
        p = base / rel
        ok = p.is_file() and p.stat().st_size > 0
        results.append(CheckResult(f"file_{key}", PASS if ok else FAIL,
                                   rel if ok else f"Soubor chybí nebo je prázdný: {rel}"))
    return results


def check_thumbnail(path: Path, spec: dict[str, Any]) -> list[CheckResult]:
    t = spec["thumbnail"]
    if not path.is_file():
        return [CheckResult("thumbnail", FAIL, f"Chybí {path.name}")]
    try:
        probe = ffprobe(path)
        s = next(s for s in probe["streams"] if s["codec_type"] == "video")
    except (ToolError, StopIteration):
        return [CheckResult("thumbnail", FAIL, "Náhled není čitelný obrázek")]
    w, h = int(s["width"]), int(s["height"])
    mb = path.stat().st_size / 1_048_576
    ok_dim = w >= t["min_width"] and h >= t["min_height"]
    ok_size = mb <= t["max_size_mb"]
    return [
        CheckResult("thumbnail_resolution", PASS if ok_dim else FAIL,
                    f"{w}x{h}" if ok_dim else
                    f"Náhled {w}x{h}, min {t['min_width']}x{t['min_height']}",
                    {"width": w, "height": h}),
        CheckResult("thumbnail_size", PASS if ok_size else FAIL,
                    f"{mb:.2f} MB" if ok_size else f"Náhled {mb:.2f} MB > {t['max_size_mb']} MB",
                    {"size_mb": mb}),
    ]
