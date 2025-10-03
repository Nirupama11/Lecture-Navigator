from __future__ import annotations

from app.services.transcript import load_vtt, load_srt


def test_parse_vtt(tmp_path):
    vtt = tmp_path / "a.vtt"
    vtt.write_text("""WEBVTT

00:00:00.000 --> 00:00:05.000
Hello world

00:00:04.000 --> 00:00:09.000
Second line
""", encoding='utf-8')
    segs = load_vtt(str(vtt))
    assert segs and segs[0]['start_time'] == 0.0


def test_parse_srt(tmp_path):
    srt = tmp_path / "a.srt"
    srt.write_text("""1
00:00:00,000 --> 00:00:03,000
Hello world

2
00:00:02,500 --> 00:00:05,000
Second line
""", encoding='utf-8')
    segs = load_srt(str(srt))
    assert segs and segs[0]['start_time'] == 0.0



