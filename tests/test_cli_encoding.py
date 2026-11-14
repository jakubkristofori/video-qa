import os
import subprocess
import sys


def test_cli_survives_legacy_console_encoding(tmp_path):
    # regrese: na českých Windows (stdout cp1250) spadl výpis ✓/✗ na UnicodeEncodeError
    ep = tmp_path / "ep"
    ep.mkdir()
    (ep / "config.yaml").write_text("name: enc\nfiles: {}\n", encoding="utf-8")
    env = {**os.environ, "PYTHONIOENCODING": "cp1250", "PYTHONUTF8": "0"}
    proc = subprocess.run(
        [sys.executable, "-m", "video_qa.cli", str(ep), "--report-dir", str(tmp_path / "r")],
        capture_output=True, env=env, check=False)
    assert b"UnicodeEncodeError" not in proc.stderr
    assert proc.returncode == 1  # chybí video i metadata
    assert "✗".encode() in proc.stdout
