from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .report import console_summary, write_html, write_json, write_junit
from .runner import run_episode


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="video-qa", description="Kontrola kvality epizody")
    p.add_argument("episodes", nargs="+", type=Path, help="složky epizod (s config.yaml)")
    p.add_argument("--report-dir", type=Path, default=Path("reports"))
    args = p.parse_args(argv)

    args.report_dir.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    for ep in args.episodes:
        report = run_episode(ep)
        print(console_summary(report))
        base = args.report_dir / report.episode
        write_json(report, base.with_suffix(".json"))
        write_junit(report, base.with_suffix(".xml"))
        write_html(report, base.with_suffix(".html"))
        if not report.ok:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
