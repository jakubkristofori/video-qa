import subprocess

from video_qa.checks.files import check_required_files, check_thumbnail
from video_qa.checks.metadata import check_metadata
from video_qa.models import FAIL, PASS, WARN

GOOD_META = {
    "title": "Tutu and the Rainbow | Nursery Rhyme for Kids",
    "description": "A fun rhyme for kids.",
    "tags": ["kids", "nursery rhymes", "tutu"],
    "language": "en",
    "made_for_kids": True,
}


def status(results):
    return {r.name: r.status for r in results}


def test_good_metadata_passes(spec):
    assert set(status(check_metadata(GOOD_META, spec)).values()) == {PASS}


def test_missing_metadata_section(spec):
    assert check_metadata(None, spec)[0].status == FAIL


def test_title_too_long(spec):
    meta = {**GOOD_META, "title": "x" * 101}
    assert status(check_metadata(meta, spec))["title"] == FAIL


def test_title_with_angle_brackets(spec):
    meta = {**GOOD_META, "title": "Bad <title>"}
    assert status(check_metadata(meta, spec))["title"] == FAIL


def test_tags_too_long(spec):
    meta = {**GOOD_META, "tags": ["abcdefghij"] * 60}
    assert status(check_metadata(meta, spec))["tags"] == FAIL


def test_missing_tags_fail_by_default(spec):
    meta = {**GOOD_META, "tags": []}
    assert status(check_metadata(meta, spec))["tags"] == FAIL


def test_missing_tags_allowed_for_shorts(spec):
    relaxed = {**spec, "metadata": {**spec["metadata"], "require_tags": False}}
    assert status(check_metadata({**GOOD_META, "tags": []}, relaxed))["tags"] == PASS


def test_too_long_tags_still_fail_when_tags_optional(spec):
    relaxed = {**spec, "metadata": {**spec["metadata"], "require_tags": False}}
    meta = {**GOOD_META, "tags": ["abcdefghij"] * 60}
    assert status(check_metadata(meta, relaxed))["tags"] == FAIL


def test_made_for_kids_must_be_explicit(spec):
    meta = {k: v for k, v in GOOD_META.items() if k != "made_for_kids"}
    assert status(check_metadata(meta, spec))["made_for_kids"] == FAIL


def test_missing_language_is_only_warning(spec):
    meta = {k: v for k, v in GOOD_META.items() if k != "language"}
    assert status(check_metadata(meta, spec))["language"] == WARN


def test_required_files(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x")
    (tmp_path / "empty.srt").write_bytes(b"")
    res = status(check_required_files(
        tmp_path, {"video": "a.mp4", "subs": "empty.srt", "thumb": "missing.png"}))
    assert res == {"file_video": PASS, "file_subs": FAIL, "file_thumb": FAIL}


def _png(path, size):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc2=s={size}:d=1", "-frames:v", "1", str(path)], check=True)


def test_thumbnail_ok(tmp_path, spec):
    p = tmp_path / "t.png"
    _png(p, "1280x720")
    assert all(r.status == PASS for r in check_thumbnail(p, spec))


def test_thumbnail_too_small(tmp_path, spec):
    p = tmp_path / "t.png"
    _png(p, "640x360")
    assert status(check_thumbnail(p, spec))["thumbnail_resolution"] == FAIL


def test_thumbnail_failure_message_says_what_is_wrong(tmp_path, spec):
    # regrese: text chyby se dřív ukládal do `details` a v reportu zůstalo jen "640x360"
    p = tmp_path / "t.png"
    _png(p, "640x360")
    res = {r.name: r for r in check_thumbnail(p, spec)}
    assert "min 1280x720" in res["thumbnail_resolution"].message
    assert res["thumbnail_resolution"].details == {"width": 640, "height": 360}


def test_thumbnail_missing(tmp_path, spec):
    assert check_thumbnail(tmp_path / "nope.png", spec)[0].status == FAIL
