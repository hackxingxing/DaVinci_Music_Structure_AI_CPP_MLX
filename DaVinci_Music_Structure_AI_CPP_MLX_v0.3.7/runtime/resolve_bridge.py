#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from apply_logic import apply_analysis, clear_markers
from resolve_api import get_resolve

def emit(data, code=0): print(json.dumps(data,ensure_ascii=False)); raise SystemExit(code)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--ping",action="store_true"); ap.add_argument("--job"); ap.add_argument("--analysis"); ap.add_argument("--candidate-index",type=int,default=0); ap.add_argument("--segments",type=int,default=1); ap.add_argument("--downbeats",type=int,default=1); ap.add_argument("--beats",type=int,default=1); ap.add_argument("--clear",action="store_true"); args=ap.parse_args()
    resolve=get_resolve()
    if args.ping:
        pm=resolve.GetProjectManager(); project=pm.GetCurrentProject() if pm else None; emit({"ok":True,"connected":True,"project":project.GetName() if project else None})
    if not args.job: ap.error("--job is required")
    job=json.loads(Path(args.job).read_text(encoding="utf-8"))
    if args.clear: emit(clear_markers(resolve,job,args.candidate_index))
    if not args.analysis: ap.error("--analysis is required")
    analysis=json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    emit(apply_analysis(resolve,job,args.candidate_index,analysis,bool(args.segments),bool(args.downbeats),bool(args.beats)))
if __name__=="__main__":
    try: main()
    except SystemExit: raise
    except Exception as exc:
        print(json.dumps({"ok":False,"error":str(exc),"traceback":traceback.format_exc()},ensure_ascii=False)); raise SystemExit(2)
