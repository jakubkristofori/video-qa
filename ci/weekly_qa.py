"""Weekly QA of real episodes, run by the self-hosted GitLab Runner on the video PC (tag `video-pc`).

The videos never leave the PC: this script runs the existing quality gate (qa_gate.py in the rainbow-rhymes repo)
locally and copies ONLY the JUnit XML and HTML summaries into --out, with local paths stripped, so that GitLab
gets nothing but test results.

usage: python -I ci/weekly_qa.py [--out reports]
  env QA_DAYS   check episodes whose final video changed in the last N days (default 7, 0 = all)
  env EPISODE   check only this episode folder name (e.g. d23_kalendar); overrides QA_DAYS
exit code: 0 all passed (or nothing to check), 1 at least one check failed, 2 the gate could not run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("E:/ComfyUI")
GATE = ROOT / "Hadanky" / "pipeline" / "qa_gate.py"
REPORTS = ROOT / "tools" / "qa_reports"
JOB_GLOBS = ["Hadanky/*/youtube/publish*.json", "Hvezdy/*/youtube/publish*.json",
             "Timmy/*/youtube/publish*.json", "NickelOwl/dily/*/youtube/publish*.json"]
# anything that would reveal the local disk layout is replaced before a result leaves the PC
PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/](?:[^\s\"'<>|]*[\\/])?")


def find_jobs() -> list[Path]:
    jobs = []
    for pattern in JOB_GLOBS:
        jobs += [j for j in ROOT.glob(pattern) if ".state" not in j.name]
    return sorted(jobs)


def episode_name(job: Path) -> str:
    """Same naming as qa_gate.build_config: <episode>, <episode>_short, <episode>_short1 ..."""
    return job.parent.parent.name + job.stem.removeprefix("publish")


def video_mtime(job: Path) -> float | None:
    try:
        video = (job.parent / json.loads(job.read_text(encoding="utf-8"))["video"]).resolve()
        return video.stat().st_mtime
    except (OSError, ValueError, KeyError):
        return None


def select(jobs: list[Path], days: int, episode: str | None) -> list[Path]:
    if episode:
        return [j for j in jobs if j.parent.parent.name == episode]
    if days <= 0:
        return [j for j in jobs if video_mtime(j) is not None]
    since = time.time() - days * 86400
    return [j for j in jobs if (video_mtime(j) or 0) >= since]


def scrub(text: str) -> str:
    return PATH_RE.sub("", text)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=Path("reports"))
    args = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    days = int(os.environ.get("QA_DAYS") or 7)
    episode = os.environ.get("EPISODE") or None
    chosen = select(find_jobs(), days, episode)
    scope = f"episode {episode}" if episode else ("all episodes" if days <= 0 else f"videos changed in the last {days} days")
    print(f"weekly-qa: {len(chosen)} publish job(s), {scope}")
    if not chosen:
        if episode:
            print(f"weekly-qa: no publish job for episode {episode!r}")
            return 2
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    worst, summary = 0, []
    for job in chosen:
        name = episode_name(job)
        run = subprocess.run([sys.executable, "-I", str(GATE), str(job)], check=False,
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(scrub(run.stdout + run.stderr).rstrip())
        worst = max(worst, run.returncode)
        summary.append((name, run.returncode))
        for ext in ("xml", "html"):
            src = REPORTS / name / "reports" / f"{name}.{ext}"
            if src.exists():
                (args.out / src.name).write_text(scrub(src.read_text(encoding="utf-8")), encoding="utf-8")

    print("\nweekly-qa summary:")
    for name, code in summary:
        print(f"  {'OK  ' if code == 0 else 'FAIL'} {name}")
    return min(worst, 2)


if __name__ == "__main__":
    sys.exit(main())
