import shutil
import subprocess

import yaml

from video_qa.cli import main
from video_qa.runner import run_episode

META = {
    "title": "Tutu episode 1",
    "description": "Rhyme",
    "tags": ["kids"],
    "language": "en",
    "made_for_kids": True,
}
SPEC = {"technical": {"width": 640, "height": 360, "min_duration_s": 5}}


def _episode(tmp_path, video, name="ep1", meta=None):
    d = tmp_path / name
    d.mkdir()
    shutil.copy(video, d / "final.mp4")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=s=1280x720:d=1", "-frames:v", "1", str(d / "thumb.png")], check=True)
    cfg = {"name": name, "files": {"video": "final.mp4", "thumbnail": "thumb.png"},
           "metadata": META if meta is None else meta, "spec": SPEC}
    (d / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return d


def test_good_episode_passes(tmp_path, vids):
    report = run_episode(_episode(tmp_path, vids["good"]))
    assert report.ok, [(r.name, r.message) for r in report.failed]


def test_bad_episode_reports_all_problems(tmp_path, vids):
    report = run_episode(_episode(tmp_path, vids["black"], meta={}))
    names = {r.name for r in report.failed}
    assert {"black_frames", "metadata"} <= names


def test_cli_exit_codes_and_reports(tmp_path, vids):
    good = _episode(tmp_path, vids["good"], "good")
    bad = _episode(tmp_path, vids["loud"], "bad")
    out = tmp_path / "reports"
    assert main([str(good), "--report-dir", str(out)]) == 0
    assert main([str(bad), "--report-dir", str(out)]) == 1
    for ext in ("json", "xml", "html"):
        assert (out / f"bad.{ext}").is_file()
