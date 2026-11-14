from __future__ import annotations

from typing import Any

from ..ffmpeg_utils import duration, first_stream, parse_fraction
from ..models import FAIL, PASS, CheckResult


def check_technical(probe: dict[str, Any], spec: dict[str, Any], size_bytes: int) -> list[CheckResult]:
    t = spec["technical"]
    v = first_stream(probe, "video")
    a = first_stream(probe, "audio")
    results: list[CheckResult] = []

    def add(name: str, ok: bool, msg_ok: str, msg_fail: str, **details: Any) -> None:
        results.append(CheckResult(name, PASS if ok else FAIL, msg_ok if ok else msg_fail, details))

    if v is None:
        return [CheckResult("video_stream", FAIL, "Soubor neobsahuje video stopu")]

    w, h = int(v["width"]), int(v["height"])
    add("resolution", (w, h) == (t["width"], t["height"]),
        f"{w}x{h}", f"Rozlišení {w}x{h}, očekáváno {t['width']}x{t['height']}", width=w, height=h)

    fps = parse_fraction(v.get("avg_frame_rate", "0/1"))
    add("fps", abs(fps - t["fps"]) <= t["fps_tolerance"],
        f"{fps:.2f} fps", f"{fps:.2f} fps, očekáváno {t['fps']}", fps=fps)

    add("video_codec", v.get("codec_name") == t["video_codec"],
        v.get("codec_name", "?"), f"Kodek {v.get('codec_name')}, očekáván {t['video_codec']}")
    add("pix_fmt", v.get("pix_fmt") == t["pix_fmt"],
        v.get("pix_fmt", "?"), f"pix_fmt {v.get('pix_fmt')}, očekáván {t['pix_fmt']}")

    audio_streams = [s for s in probe["streams"] if s.get("codec_type") == "audio"]
    add("audio_streams", len(audio_streams) == t["audio_streams"],
        f"{len(audio_streams)} audio stopa", f"Počet audio stop {len(audio_streams)}, očekáváno {t['audio_streams']}")
    if a is not None:
        add("audio_codec", a.get("codec_name") == t["audio_codec"],
            a.get("codec_name", "?"), f"Audio kodek {a.get('codec_name')}, očekáván {t['audio_codec']}")
        sr = int(a.get("sample_rate", 0))
        add("sample_rate", sr in t["sample_rates"], f"{sr} Hz", f"Vzorkování {sr} Hz, povoleno {t['sample_rates']}")

    d = duration(probe)
    add("duration", t["min_duration_s"] <= d <= t["max_duration_s"],
        f"{d:.1f} s", f"Délka {d:.1f} s mimo rozsah {t['min_duration_s']}–{t['max_duration_s']} s", seconds=d)

    mb = size_bytes / 1_048_576
    add("file_size", mb <= t["max_size_mb"], f"{mb:.1f} MB", f"Soubor {mb:.1f} MB > {t['max_size_mb']} MB")
    return results
