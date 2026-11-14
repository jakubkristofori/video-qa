"""Generátor syntetických videí: dobré i záměrně vadné vzorky pro testování kontrol."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from video_qa.runner import load_default_spec

W, H = 640, 360


def make_video(
    path: Path,
    video: list[tuple[str, float]],
    audio: list[tuple[str, float, float]] | None,
    *,
    size: tuple[int, int] = (W, H),
    fps: int = 30,
) -> Path:
    """video: [("pattern"|"black"|"static", sekundy)], audio: [("tone"|"silence", sekundy, gain_dB)]."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    w, h = size
    filters: list[str] = []
    n = 0
    for kind, secs in video:
        src = {
            "pattern": f"testsrc2=s={w}x{h}:r={fps}:d={secs}",
            "black": f"color=c=black:s={w}x{h}:r={fps}:d={secs}",
            "static": f"color=c=0x2255aa:s={w}x{h}:r={fps}:d={secs}",
        }[kind]
        cmd += ["-f", "lavfi", "-i", src]
        filters.append(f"[{n}:v]format=yuv420p,setsar=1[v{n}]")
        n += 1
    vlabels = "".join(f"[v{i}]" for i in range(n))
    filters.append(f"{vlabels}concat=n={n}:v=1:a=0[vout]")

    maps = ["-map", "[vout]"]
    if audio:
        a0 = n
        for kind, secs, gain in audio:
            src = (f"sine=f=440:r=48000:d={secs}" if kind == "tone"
                   else f"anullsrc=r=48000:cl=stereo:d={secs}")
            cmd += ["-f", "lavfi", "-i", src]
            vol = f",volume={gain}dB" if kind == "tone" else ""
            filters.append(
                f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo{vol}[a{n}]")
            n += 1
        alabels = "".join(f"[a{i}]" for i in range(a0, n))
        filters.append(f"{alabels}concat=n={n - a0}:v=0:a=1[aout]")
        maps += ["-map", "[aout]"]

    cmd += ["-filter_complex", ";".join(filters), *maps,
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-r", str(fps)]
    if audio:
        cmd += ["-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "128k"]
    cmd += [str(path)]
    subprocess.run(cmd, check=True)
    return path


GOOD_V = [("pattern", 8.0)]
GOOD_A = [("tone", 8.0, 7.8)]  # ≈ -14 LUFS


@pytest.fixture(scope="session")
def spec():
    s = load_default_spec()
    s["technical"].update(width=W, height=H, min_duration_s=5)
    return s


@pytest.fixture(scope="session")
def vids(tmp_path_factory):
    d = tmp_path_factory.mktemp("vids")
    return {
        "good": make_video(d / "good.mp4", GOOD_V, GOOD_A),
        "black": make_video(d / "black.mp4",
                            [("pattern", 3), ("black", 2), ("pattern", 3)], GOOD_A),
        "fade_end": make_video(d / "fade_end.mp4",
                               [("pattern", 6), ("black", 2)], GOOD_A),
        "frozen": make_video(d / "frozen.mp4",
                             [("pattern", 2), ("static", 5), ("pattern", 1)], GOOD_A),
        "loud": make_video(d / "loud.mp4", GOOD_V, [("tone", 8.0, 24.0)]),
        "quiet": make_video(d / "quiet.mp4", GOOD_V, [("tone", 8.0, -10.0)]),
        "lead_silence": make_video(d / "lead.mp4", GOOD_V,
                                   [("silence", 3.0, 0), ("tone", 5.0, 7.8)]),
        "trail_silence": make_video(d / "trail.mp4", GOOD_V,
                                    [("tone", 5.0, 7.8), ("silence", 3.0, 0)]),
        "no_audio": make_video(d / "noaudio.mp4", GOOD_V, None),
        "wrong_fps": make_video(d / "fps25.mp4", GOOD_V, GOOD_A, fps=25),
        "wrong_res": make_video(d / "res.mp4", GOOD_V, GOOD_A, size=(480, 270)),
    }
