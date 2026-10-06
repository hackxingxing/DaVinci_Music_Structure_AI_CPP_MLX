from __future__ import annotations
import json,sys
from pathlib import Path
RUNTIME=Path.home()/"Library"/"Application Support"/"MusicStructureAI_CPP"; MODULES=RUNTIME/"runtime"
if str(MODULES) not in sys.path:sys.path.insert(0,str(MODULES))
from apply_logic import apply_analysis
from resolve_api import get_resolve
p=RUNTIME/"pending.json"
if not p.exists():raise RuntimeError("没有待写入的分析结果。请先运行 Music Structure AI。")
pending=json.loads(p.read_text(encoding="utf-8")); job=json.loads(Path(pending["job"]).read_text(encoding="utf-8")); analysis=json.loads(Path(pending["analysis"]).read_text(encoding="utf-8"))
print(json.dumps(apply_analysis(get_resolve(),job,int(pending["candidate_index"]),analysis,bool(pending.get("segments",True)),bool(pending.get("downbeats",True)),bool(pending.get("beats",True))),ensure_ascii=False))
