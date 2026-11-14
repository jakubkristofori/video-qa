import pytest

from video_qa.checks.audio import check_loudness, check_silence_edges
from video_qa.checks.technical import check_technical
from video_qa.checks.video import check_black_frames, check_freeze
from video_qa.ffmpeg_utils import duration, ffprobe
from video_qa.models import FAIL, PASS


def by_name(results):
    return {r.name: r for r in results}


def test_good_video_passes_technical(vids, spec):
    p = vids["good"]
    res = check_technical(ffprobe(p), spec, p.stat().st_size)
    failed = [r for r in res if r.status == FAIL]
    assert not failed, [(r.name, r.message) for r in failed]


@pytest.mark.parametrize("key,failing", [("wrong_res", "resolution"), ("wrong_fps", "fps")])
def test_technical_detects_wrong_format(vids, spec, key, failing):
    p = vids[key]
    res = by_name(check_technical(ffprobe(p), spec, p.stat().st_size))
    assert res[failing].status == FAIL


def test_duration_out_of_range(vids, spec):
    strict = {**spec, "technical": {**spec["technical"], "min_duration_s": 60}}
    p = vids["good"]
    assert by_name(check_technical(ffprobe(p), strict, p.stat().st_size))["duration"].status == FAIL


def test_good_loudness_passes(vids, spec):
    res = by_name(check_loudness(vids["good"], spec))
    assert res["loudness"].status == PASS, res["loudness"].message
    assert res["true_peak"].status == PASS


def test_too_loud_fails(vids, spec):
    res = by_name(check_loudness(vids["loud"], spec))
    assert res["loudness"].status == FAIL
    assert res["true_peak"].status == FAIL


def test_too_quiet_fails(vids, spec):
    assert by_name(check_loudness(vids["quiet"], spec))["loudness"].status == FAIL


def test_leading_silence_detected(vids, spec):
    p = vids["lead_silence"]
    res = by_name(check_silence_edges(p, ffprobe(p), spec))
    assert res["leading_silence"].status == FAIL
    assert res["trailing_silence"].status == PASS


def test_trailing_silence_detected(vids, spec):
    p = vids["trail_silence"]
    res = by_name(check_silence_edges(p, ffprobe(p), spec))
    assert res["trailing_silence"].status == FAIL
    assert res["leading_silence"].status == PASS


def test_good_video_has_no_silence_problem(vids, spec):
    p = vids["good"]
    assert all(r.status == PASS for r in check_silence_edges(p, ffprobe(p), spec))


def test_black_segment_detected(vids, spec):
    r = check_black_frames(vids["black"], spec)
    assert r.status == FAIL
    assert 2.5 <= r.details["segments"][0]["start"] <= 3.5


def _allow_end(spec, seconds):
    return {**spec, "video": {**spec["video"], "allow_black_at_end_s": seconds}}


def test_black_at_end_fails_by_default(vids, spec):
    p = vids["fade_end"]
    assert check_black_frames(p, spec, duration(ffprobe(p))).status == FAIL


def test_black_at_end_tolerated_when_allowed(vids, spec):
    p = vids["fade_end"]
    assert check_black_frames(p, _allow_end(spec, 3), duration(ffprobe(p))).status == PASS


def test_allowed_end_black_does_not_hide_black_in_the_middle(vids, spec):
    p = vids["black"]  # černá je uprostřed, ne na konci
    assert check_black_frames(p, _allow_end(spec, 3), duration(ffprobe(p))).status == FAIL


def test_no_black_in_good(vids, spec):
    assert check_black_frames(vids["good"], spec).status == PASS


def test_freeze_detected(vids, spec):
    r = check_freeze(vids["frozen"], spec)
    assert r.status == FAIL


def test_no_freeze_in_good(vids, spec):
    assert check_freeze(vids["good"], spec).status == PASS
