from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from core import AudioCandidate, build_marker_plan, playhead_frame_from_timecodes, timecode_to_frames


def test_non_drop_timecode():
    assert timecode_to_frames("01:00:00:00", 24.0) == 86400
    assert playhead_frame_from_timecodes("01:00:10:00", "01:00:00:00", 0, 24.0) == 240


def test_drop_frame_2997():
    # SMPTE drop-frame: 01:00:00;00 equals 107892 nominal frame counts after dropped labels.
    assert timecode_to_frames("01:00:00;00", 29.97) == 107892


def test_marker_plan():
    c = AudioCandidate(
        track_index=1,
        track_name="Music",
        item=None,
        media_pool_item=None,
        name="song.wav",
        path="/tmp/song.wav",
        timeline_start=100,
        timeline_end=340,
        source_start_seconds=10.0,
        source_end_seconds=20.0,
    )
    analysis = {
        "bpm": 120,
        "segments": [
            {"start": 0, "end": 5, "label": "verse"},
            {"start": 5, "end": 10, "label": "chorus"},
        ],
        "beats": [0, 0.5, 1.0, 1.5],
        "beat_positions": [1, 2, 3, 4],
        "downbeats": [0],
    }
    plan = build_marker_plan(analysis, c, timeline_start_frame=0)
    assert len(plan["timeline"]) == 2
    assert plan["timeline"][0]["frame"] == 100
    assert plan["timeline"][0]["duration"] == 120
    assert len(plan["clip"]) == 4
    assert plan["clip"][0]["color"] == "Cyan"

class _MPI:
    def GetClipProperty(self, key=None):
        if key == "File Path":
            return "/tmp/music.wav"
        return {"File Path": "/tmp/music.wav"}
    def GetName(self):
        return "music.wav"

class _Item:
    def GetStart(self, *args): return 100
    def GetEnd(self, *args): return 200
    def GetSourceStartTime(self): return 2.0
    def GetSourceEndTime(self): return 6.0
    def GetMediaPoolItem(self): return _MPI()
    def GetName(self): return "music.wav"

class _Timeline:
    def GetTrackCount(self, kind): return 1
    def GetItemListInTrack(self, kind, idx): return [_Item()]
    def GetTrackName(self, kind, idx): return "Music"


def test_find_candidate_at_playhead():
    from core import find_audio_candidates_at_playhead
    found = find_audio_candidates_at_playhead(_Timeline(), 150)
    assert len(found) == 1
    assert found[0].path == "/tmp/music.wav"
    assert found[0].source_duration == 4.0

class _MarkerOwner:
    def __init__(self):
        self.markers = {10: {"name": "user marker", "customData": ""}}
        self.added = []
    def GetMarkers(self):
        return self.markers
    def AddMarker(self, frame, color, name, note, duration, customData=""):
        self.added.append(frame)
        self.markers[frame] = {"name": name, "customData": customData}
        return True


def test_marker_collision_preserves_timing_by_skipping():
    from core import add_markers
    owner = _MarkerOwner()
    added, skipped = add_markers(owner, [{
        "frame": 10, "color": "Blue", "name": "beat", "note": "", "duration": 1, "customData": "MSAI:v0.3:beat"
    }], avoid_existing=True)
    assert added == 0
    assert skipped == 1
    assert owner.added == []


def test_segment_names_are_chinese_numbered():
    c = AudioCandidate(
        track_index=1, track_name="Music", item=None, media_pool_item=None,
        name="song.wav", path="/tmp/song.wav",
        timeline_start=0, timeline_end=2400,
        source_start_seconds=0.0, source_end_seconds=100.0,
    )
    analysis = {
        "segments": [
            {"start": 0, "end": 10, "label": "intro"},
            {"start": 10, "end": 30, "label": "verse"},
            {"start": 30, "end": 50, "label": "chorus"},
            {"start": 50, "end": 70, "label": "verse"},
            {"start": 70, "end": 90, "label": "chorus"},
            {"start": 90, "end": 100, "label": "outro"},
        ],
        "beats": [],
    }
    plan = build_marker_plan(analysis, c, 0, include_downbeats=False, include_beats=False)
    names = [m["name"] for m in plan["timeline"]]
    assert names == ["01 前奏", "02 主歌 1", "03 副歌 1", "04 主歌 2", "05 副歌 2", "06 尾奏"]
    colors = [m["color"] for m in plan["timeline"]]
    assert colors == ["Blue", "Green", "Red", "Green", "Red", "Yellow"]
    assert all("/" not in n for n in names)
