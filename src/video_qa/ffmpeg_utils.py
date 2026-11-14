from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


class ToolError(RuntimeError):
    pass


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        raise ToolError(f"Nástroj '{cmd[0]}' není nainstalovaný (potřebuješ ffmpeg).") from e


def ffprobe(path: Path) -> dict[str, Any]:
    proc = _run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
         str(path)]
    )
    if proc.returncode != 0:
        raise ToolError(f"ffprobe selhal pro {path}: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def ffmpeg_filter_log(path: Path, *, vf: str | None = None, af: str | None = None) -> str:
    """Spustí filtr a vrátí stderr (tam ffmpeg píše výsledky detekce)."""
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path)]
    if vf:
        cmd += ["-vf", vf, "-an"]
    if af:
        cmd += ["-af", af, "-vn"]
    cmd += ["-f", "null", "-"]
    proc = _run(cmd)
    if proc.returncode != 0:
        raise ToolError(f"ffmpeg selhal pro {path}: {proc.stderr.strip()[-500:]}")
    return proc.stderr


def parse_fraction(value: str) -> float:
    num, _, den = value.partition("/")
    return float(num) / float(den) if den and float(den) else float(num)


def first_stream(probe: dict[str, Any], kind: str) -> dict[str, Any] | None:
    return next((s for s in probe.get("streams", []) if s.get("codec_type") == kind), None)


def duration(probe: dict[str, Any]) -> float:
    return float(probe["format"].get("duration", 0))


def find_floats(pattern: str, text: str) -> list[float]:
    return [float(m) for m in re.findall(pattern, text)]
