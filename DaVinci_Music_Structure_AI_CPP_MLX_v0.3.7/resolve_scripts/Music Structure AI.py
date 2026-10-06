from __future__ import annotations
import json, os, subprocess, sys, time, traceback, uuid
from pathlib import Path
RUNTIME=Path.home()/"Library"/"Application Support"/"MusicStructureAI_CPP"; MODULES=RUNTIME/"runtime"
if str(MODULES) not in sys.path: sys.path.insert(0,str(MODULES))
from core import analysis_cache_key, find_audio_candidates_at_playhead, playhead_frame_from_timecodes
from resolve_api import get_resolve
APP_BIN=Path.home()/"Applications"/"Music Structure AI.app"/"Contents"/"MacOS"/"MusicStructureAI"; JOBS=Path.home()/"Library"/"Caches"/"MusicStructureAI_CPP"/"jobs"; LOGDIR=Path.home()/"Library"/"Logs"/"MusicStructureAI_CPP"
def timeline_fps(project,timeline):
    for key in ("timelineFrameRate","timelinePlaybackFrameRate"):
        try:
            v=timeline.GetSetting(key)
            if v:return float(v)
        except Exception:pass
    try:
        v=project.GetSetting("timelineFrameRate")
        if v:return float(v)
    except Exception:pass
    return 24.0
def main():
    LOGDIR.mkdir(parents=True,exist_ok=True); JOBS.mkdir(parents=True,exist_ok=True)
    if not APP_BIN.exists(): raise RuntimeError("C++ 控制器没有安装。请重新运行 v0.3 的 install.command。")
    resolve=get_resolve(); pm=resolve.GetProjectManager(); project=pm.GetCurrentProject() if pm else None
    if not project: raise RuntimeError("当前没有打开项目。")
    timeline=project.GetCurrentTimeline()
    if not timeline: raise RuntimeError("当前没有时间线。")
    fps=timeline_fps(project,timeline); ph=playhead_frame_from_timecodes(timeline.GetCurrentTimecode(),timeline.GetStartTimecode(),int(timeline.GetStartFrame()),fps); candidates=find_audio_candidates_at_playhead(timeline,ph)
    if not candidates: raise RuntimeError("播放头位置没有检测到音频 Clip。请把播放头放在音乐片段内部。")
    jid=uuid.uuid4().hex; d=JOBS/jid; d.mkdir(parents=True,exist_ok=True)
    payload={"schema":1,"job_id":jid,"created_at":time.time(),"project_name":project.GetName(),"timeline_name":timeline.GetName(),"timeline_start_frame":int(timeline.GetStartFrame()),"timeline_start_timecode":timeline.GetStartTimecode(),"timeline_fps":fps,"playhead_frame":ph,"candidates":[]}
    for c in candidates:
        payload["candidates"].append({"track_index":c.track_index,"track_name":c.track_name,"name":c.name,"path":c.path,"timeline_start":c.timeline_start,"timeline_end":c.timeline_end,"source_start_seconds":c.source_start_seconds,"source_end_seconds":c.source_end_seconds,"source_duration_seconds":c.source_duration,"display_name":c.display_name(),"cache_key":analysis_cache_key(c)})
    job=d/"job.json"; job.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    log=(LOGDIR/"launcher.log").open("a",encoding="utf-8")
    subprocess.Popen([str(APP_BIN),"--job",str(job)],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,"PATH":"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:"+os.environ.get("PATH","")},start_new_session=True)
try: main()
except Exception:
    LOGDIR.mkdir(parents=True,exist_ok=True)
    with (LOGDIR/"launcher.log").open("a",encoding="utf-8") as f:f.write(traceback.format_exc()+"\n")
    raise
