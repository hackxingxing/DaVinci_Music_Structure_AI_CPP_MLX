from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

PLUGIN_PREFIX = "MSAI:"
PLUGIN_TAG = "MSAI:v0.3.7-cpp"

LABELS_ZH = {
    "start": "开始",
    "end": "结束",
    "intro": "前奏",
    "outro": "尾奏",
    "break": "间奏",
    "bridge": "桥段",
    "inst": "器乐段",
    "solo": "独奏段",
    "verse": "主歌",
    "chorus": "副歌",
}

SEGMENT_COLORS = {
    "intro": "Blue",
    "verse": "Green",
    "chorus": "Red",
    "bridge": "Purple",
    "outro": "Yellow",
    "break": "Pink",
    "inst": "Cyan",
    "solo": "Cyan",
    "start": "Blue",
    "end": "Yellow",
}


def _nominal_fps(fps: float) -> int:
    if fps <= 0:
        return 24
    return int(round(fps))


def timecode_to_frames(timecode: str, fps: float) -> int:
    """Convert SMPTE timecode to an absolute frame number.

    Handles normal timecode and the common 29.97/59.94 drop-frame forms.
    For 23.976 non-drop projects the nominal count is 24 fps, matching SMPTE display.
    """
    if not timecode:
        raise ValueError("Empty timecode")

    drop = ";" in timecode
    parts = [int(p) for p in re.split(r"[:;]", timecode.strip())]
    if len(parts) != 4:
        raise ValueError(f"Unsupported timecode: {timecode}")
    hh, mm, ss, ff = parts
    nominal = _nominal_fps(fps)
    total = ((hh * 3600 + mm * 60 + ss) * nominal) + ff

    if drop:
        if abs(fps - 29.97) < 0.05 or abs(fps - 29.97002997) < 0.05:
            drop_frames = 2
        elif abs(fps - 59.94) < 0.05 or abs(fps - 59.94005994) < 0.05:
            drop_frames = 4
        else:
            drop_frames = 0
        if drop_frames:
            total_minutes = hh * 60 + mm
            total -= drop_frames * (total_minutes - total_minutes // 10)
    return total


def playhead_frame_from_timecodes(
    current_tc: str,
    start_tc: str,
    timeline_start_frame: int,
    fps: float,
) -> int:
    current = timecode_to_frames(current_tc, fps)
    start = timecode_to_frames(start_tc, fps)
    diff = current - start
    nominal = _nominal_fps(fps)
    day = 24 * 3600 * nominal
    if diff < -(day // 2):
        diff += day
    elif diff > day // 2:
        diff -= day
    return int(round(timeline_start_frame + diff))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_file_path(media_pool_item: Any) -> str:
    if not media_pool_item:
        return ""
    try:
        direct = media_pool_item.GetClipProperty("File Path")
        if direct:
            return str(direct)
    except Exception:
        pass
    try:
        props = media_pool_item.GetClipProperty() or {}
    except Exception:
        props = {}
    for key, value in props.items():
        normalized = str(key).strip().lower().replace("_", " ")
        if normalized in {"file path", "filepath"} and value:
            return str(value)
    return ""


@dataclass
class AudioCandidate:
    track_index: int
    track_name: str
    item: Any
    media_pool_item: Any
    name: str
    path: str
    timeline_start: float
    timeline_end: float
    source_start_seconds: float
    source_end_seconds: float

    @property
    def source_duration(self) -> float:
        return max(0.0, self.source_end_seconds - self.source_start_seconds)

    def display_name(self) -> str:
        track = self.track_name or f"A{self.track_index}"
        filename = Path(self.path).name if self.path else self.name
        return f"{track}  |  {filename}"


def find_audio_candidates_at_playhead(timeline: Any, playhead_frame: float) -> List[AudioCandidate]:
    candidates: List[AudioCandidate] = []
    count = int(timeline.GetTrackCount("audio") or 0)
    for track_index in range(1, count + 1):
        try:
            items = timeline.GetItemListInTrack("audio", track_index) or []
        except Exception:
            items = []
        try:
            track_name = timeline.GetTrackName("audio", track_index) or f"A{track_index}"
        except Exception:
            track_name = f"A{track_index}"

        for item in items:
            try:
                start = float(item.GetStart(True))
            except Exception:
                start = float(item.GetStart())
            try:
                end = float(item.GetEnd(True))
            except Exception:
                end = float(item.GetEnd())
            if not (start <= playhead_frame < end):
                continue

            try:
                mpi = item.GetMediaPoolItem()
            except Exception:
                mpi = None
            path = get_file_path(mpi)
            try:
                name = item.GetName() or (mpi.GetName() if mpi else "Audio")
            except Exception:
                name = "Audio"
            try:
                src_start = safe_float(item.GetSourceStartTime(), 0.0)
                src_end = safe_float(item.GetSourceEndTime(), 0.0)
            except Exception:
                src_start, src_end = 0.0, 0.0

            candidates.append(
                AudioCandidate(
                    track_index=track_index,
                    track_name=str(track_name),
                    item=item,
                    media_pool_item=mpi,
                    name=str(name),
                    path=path,
                    timeline_start=start,
                    timeline_end=end,
                    source_start_seconds=src_start,
                    source_end_seconds=src_end,
                )
            )
    return candidates


def analysis_cache_key(candidate: AudioCandidate) -> str:
    p = Path(candidate.path)
    try:
        stat = p.stat()
        fingerprint = f"{p.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
    except Exception:
        fingerprint = str(p)
    raw = (
        f"{fingerprint}|{candidate.source_start_seconds:.6f}|"
        f"{candidate.source_end_seconds:.6f}|{PLUGIN_TAG}"
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def source_seconds_to_clip_frame(
    seconds_from_analyzed_start: float,
    source_duration_seconds: float,
    timeline_duration_frames: float,
) -> int:
    if source_duration_seconds <= 0:
        return int(round(seconds_from_analyzed_start))
    ratio = clamp(seconds_from_analyzed_start / source_duration_seconds, 0.0, 1.0)
    return int(round(ratio * timeline_duration_frames))


def build_marker_plan(
    analysis: Dict[str, Any],
    candidate: AudioCandidate,
    timeline_start_frame: int,
    include_segments: bool = True,
    include_downbeats: bool = True,
    include_beats: bool = True,
) -> Dict[str, List[Dict[str, Any]]]:
    """Create a marker plan independent from Resolve so it can be unit-tested.

    Segment markers are timeline-range markers.
    Beat/downbeat markers are clip markers on the analyzed audio item.
    This lets segment and beat markers coexist at identical musical moments.
    """
    timeline_duration_frames = max(1.0, candidate.timeline_end - candidate.timeline_start)
    source_duration = candidate.source_duration
    if source_duration <= 0:
        # Fallback for unusual media where Resolve doesn't report source times.
        source_duration = max(
            [safe_float(s.get("end")) for s in analysis.get("segments", [])] + [0.0]
        )
        if source_duration <= 0:
            source_duration = max([safe_float(x) for x in analysis.get("beats", [])] + [1.0])

    plan: Dict[str, List[Dict[str, Any]]] = {"timeline": [], "clip": []}

    if include_segments:
        # Resolve can only show a narrow colored range when the timeline is zoomed out,
        # so use a stable color legend plus Chinese-only, numbered names.
        raw_segments = []
        for seg in analysis.get("segments", []) or []:
            label = str(seg.get("label", "")).lower()
            if label in {"start", "end", ""}:
                continue
            raw_segments.append((seg, label))

        totals: Dict[str, int] = {}
        for _, label in raw_segments:
            totals[label] = totals.get(label, 0) + 1
        seen: Dict[str, int] = {}

        for section_index, (seg, label) in enumerate(raw_segments, start=1):
            seen[label] = seen.get(label, 0) + 1
            zh = LABELS_ZH.get(label, label)
            # Repeated musical functions are easier to distinguish as 主歌 1 / 主歌 2,
            # while one-off sections stay concise (前奏 / 桥段 / 尾奏).
            zh_instance = f"{zh} {seen[label]}" if totals.get(label, 0) > 1 else zh
            s = clamp(safe_float(seg.get("start")), 0.0, source_duration)
            e = clamp(safe_float(seg.get("end")), s, source_duration)
            clip_start = source_seconds_to_clip_frame(s, source_duration, timeline_duration_frames)
            clip_end = source_seconds_to_clip_frame(e, source_duration, timeline_duration_frames)
            abs_frame = candidate.timeline_start + clip_start
            duration = max(1, clip_end - clip_start)
            plan["timeline"].append(
                {
                    "frame": int(round(abs_frame - timeline_start_frame)),
                    "duration": int(duration),
                    "color": SEGMENT_COLORS.get(label, "Blue"),
                    "name": f"{section_index:02d} {zh_instance}",
                    "note": f"第 {section_index:02d} 段｜{zh_instance}｜{s:.2f}s–{e:.2f}s",
                    "customData": f"{PLUGIN_TAG}:segment:{label}:{s:.3f}",
                }
            )

    beats = analysis.get("beats", []) or []
    positions = analysis.get("beat_positions", []) or []
    downbeats = analysis.get("downbeats", []) or []

    # If beat_positions are missing, infer downbeats by proximity to the explicit downbeat list.
    def is_downbeat(idx: int, sec: float) -> bool:
        if idx < len(positions):
            try:
                return int(positions[idx]) == 1
            except Exception:
                pass
        return any(abs(sec - safe_float(db)) <= 0.06 for db in downbeats)

    for idx, beat in enumerate(beats):
        sec = clamp(safe_float(beat), 0.0, source_duration)
        strong = is_downbeat(idx, sec)
        if strong and not include_downbeats and not include_beats:
            continue
        if not strong and not include_beats:
            continue
        clip_frame = source_seconds_to_clip_frame(sec, source_duration, timeline_duration_frames)
        pos = 1
        if idx < len(positions):
            try:
                pos = int(positions[idx])
            except Exception:
                pos = 1 if strong else 0
        plan["clip"].append(
            {
                "frame": int(clip_frame),
                "duration": 1,
                "color": "Cyan" if strong else "Blue",
                "name": "小节 / BAR 1" if strong else f"节拍 / BEAT {pos or ''}".strip(),
                "note": f"Music Structure AI · {sec:.3f}s",
                "customData": f"{PLUGIN_TAG}:beat:{idx}:{sec:.3f}",
            }
        )

    return plan


def remove_plugin_markers(marker_owner: Any, prefix: str = PLUGIN_PREFIX) -> int:
    removed = 0
    try:
        markers = marker_owner.GetMarkers() or {}
    except Exception:
        return 0
    for frame, info in list(markers.items()):
        custom = ""
        if isinstance(info, dict):
            custom = str(info.get("customData", ""))
        if custom.startswith(prefix):
            try:
                if marker_owner.DeleteMarkerAtFrame(frame):
                    removed += 1
            except Exception:
                pass
    return removed


def add_markers(marker_owner: Any, markers: Sequence[Dict[str, Any]], avoid_existing: bool = False) -> Tuple[int, int]:
    added = 0
    skipped = 0
    existing_frames = set()
    if avoid_existing:
        try:
            existing_frames = {int(round(float(k))) for k in (marker_owner.GetMarkers() or {}).keys()}
        except Exception:
            existing_frames = set()

    for marker in markers:
        frame = int(marker["frame"])
        if avoid_existing and frame in existing_frames:
            # Beat/section timing is more important than forcing every marker in.
            # Never shift a musical marker by a few frames just to avoid a collision.
            skipped += 1
            continue
        try:
            ok = marker_owner.AddMarker(
                frame,
                marker["color"],
                marker["name"],
                marker["note"],
                int(marker.get("duration", 1)),
                marker.get("customData", ""),
            )
        except TypeError:
            # Older builds that do not accept customData as the sixth arg.
            ok = marker_owner.AddMarker(
                frame,
                marker["color"],
                marker["name"],
                marker["note"],
                int(marker.get("duration", 1)),
            )
        except Exception:
            ok = False
        if ok:
            added += 1
            existing_frames.add(frame)
        else:
            skipped += 1
    return added, skipped
