from __future__ import annotations

from copy import deepcopy
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from .checks.audio import check_loudness, check_silence_edges, skip_audio
from .checks.files import check_required_files, check_thumbnail
from .checks.metadata import check_metadata
from .checks.technical import check_technical
from .checks.video import check_black_frames, check_freeze
from .ffmpeg_utils import ToolError, duration, ffprobe, first_stream
from .models import FAIL, CheckResult, Report


def load_default_spec() -> dict[str, Any]:
    text = resources.files("video_qa").joinpath("default_spec.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for k, v in (override or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(episode_dir: Path) -> dict[str, Any]:
    cfg_path = episode_dir / "config.yaml"
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Chybí {cfg_path}")
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


def run_episode(episode_dir: Path) -> Report:
    episode_dir = episode_dir.resolve()
    cfg = load_config(episode_dir)
    spec = _merge(load_default_spec(), cfg.get("spec", {}))
    report = Report(episode=cfg.get("name", episode_dir.name))
    add = report.results.extend

    files = cfg.get("files", {})
    add(check_required_files(episode_dir, files))
    add(check_metadata(cfg.get("metadata"), spec))
    if "thumbnail" in files:
        add(check_thumbnail(episode_dir / files["thumbnail"], spec))

    video_rel = files.get("video")
    video = episode_dir / video_rel if video_rel else None
    if not video or not video.is_file():
        report.results.append(CheckResult("video", FAIL, "Video soubor nenalezen – kontroly obsahu přeskočeny"))
        return report

    try:
        probe = ffprobe(video)
        add(check_technical(probe, spec, video.stat().st_size))
        if first_stream(probe, "audio"):
            add(check_loudness(video, spec))
            add(check_silence_edges(video, probe, spec))
        else:
            add(skip_audio("Video nemá audio stopu"))
        if first_stream(probe, "video"):
            report.results.append(check_black_frames(video, spec, duration(probe)))
            report.results.append(check_freeze(video, spec))
    except ToolError as e:
        report.results.append(CheckResult("tooling", FAIL, str(e)))
    return report
