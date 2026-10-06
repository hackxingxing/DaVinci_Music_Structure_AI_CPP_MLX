from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from core import AudioCandidate, add_markers, build_marker_plan, get_file_path, remove_plugin_markers, safe_float

def _same_path(a: str, b: str) -> bool:
    if not a or not b: return True
    try: return Path(a).expanduser().resolve() == Path(b).expanduser().resolve()
    except Exception: return a == b

def current_project_timeline(resolve, job: dict):
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject() if pm else None
    if not project: raise RuntimeError("Resolve 当前没有打开项目。")
    timeline = project.GetCurrentTimeline()
    if not timeline: raise RuntimeError("Resolve 当前没有时间线。")
    expected_project = str(job.get("project_name", "")); expected_timeline = str(job.get("timeline_name", ""))
    if expected_project and project.GetName() != expected_project:
        raise RuntimeError(f"项目已切换：分析时是 {expected_project}，当前是 {project.GetName()}。")
    if expected_timeline and timeline.GetName() != expected_timeline:
        raise RuntimeError(f"时间线已切换：分析时是 {expected_timeline}，当前是 {timeline.GetName()}。")
    return project, timeline

def locate_candidate(timeline, meta: dict) -> AudioCandidate:
    track_index = int(meta["track_index"]); target_start = float(meta["timeline_start"]); target_end = float(meta["timeline_end"]); target_path = str(meta.get("path", ""))
    items = timeline.GetItemListInTrack("audio", track_index) or []
    best = None; best_score = 1e18
    for item in items:
        try: start = float(item.GetStart(True))
        except Exception: start = float(item.GetStart())
        try: end = float(item.GetEnd(True))
        except Exception: end = float(item.GetEnd())
        mpi = item.GetMediaPoolItem(); path = get_file_path(mpi)
        score = abs(start-target_start)+abs(end-target_end)
        if target_path and path and not _same_path(target_path, path): score += 100000.0
        if score < best_score: best_score = score; best = (item, mpi, start, end, path)
    if best is None or best_score > 4.0: raise RuntimeError("找不到分析时的音频 Clip。请不要在分析完成前移动/替换该音乐片段。")
    item, mpi, start, end, live_path = best
    try: name = item.GetName() or (mpi.GetName() if mpi else "Audio")
    except Exception: name = "Audio"
    try: track_name = timeline.GetTrackName("audio", track_index) or f"A{track_index}"
    except Exception: track_name = f"A{track_index}"
    return AudioCandidate(track_index=track_index, track_name=str(track_name), item=item, media_pool_item=mpi, name=str(name), path=live_path or target_path, timeline_start=start, timeline_end=end, source_start_seconds=safe_float(meta.get("source_start_seconds"),0.0), source_end_seconds=safe_float(meta.get("source_end_seconds"),0.0))

def apply_analysis(resolve, job: dict, candidate_index: int, analysis: dict, include_segments: bool, include_downbeats: bool, include_beats: bool) -> Dict[str, Any]:
    _, timeline = current_project_timeline(resolve, job); candidates = job.get("candidates", [])
    if not (0 <= candidate_index < len(candidates)): raise RuntimeError("候选音乐索引无效。")
    candidate = locate_candidate(timeline, candidates[candidate_index])
    plan = build_marker_plan(analysis, candidate, int(timeline.GetStartFrame()), include_segments=include_segments, include_downbeats=include_downbeats, include_beats=include_beats)
    removed = remove_plugin_markers(timeline) + remove_plugin_markers(candidate.item)
    seg_added, seg_skipped = add_markers(timeline, plan["timeline"], avoid_existing=True)
    beat_added, beat_skipped = add_markers(candidate.item, plan["clip"], avoid_existing=True)
    return {"ok":True,"bpm":analysis.get("bpm"),"removed":removed,"segments_added":seg_added,"segments_skipped":seg_skipped,"beats_added":beat_added,"beats_skipped":beat_skipped}

def clear_markers(resolve, job: dict, candidate_index: int) -> Dict[str, Any]:
    _, timeline = current_project_timeline(resolve, job); candidates = job.get("candidates", [])
    if not (0 <= candidate_index < len(candidates)): raise RuntimeError("候选音乐索引无效。")
    candidate = locate_candidate(timeline, candidates[candidate_index])
    return {"ok":True,"removed":remove_plugin_markers(timeline)+remove_plugin_markers(candidate.item)}
