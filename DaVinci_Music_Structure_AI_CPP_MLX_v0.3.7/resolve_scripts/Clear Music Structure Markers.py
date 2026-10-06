from __future__ import annotations
import json,sys
from pathlib import Path
RUNTIME=Path.home()/"Library"/"Application Support"/"MusicStructureAI_CPP"; MODULES=RUNTIME/"runtime"
if str(MODULES) not in sys.path:sys.path.insert(0,str(MODULES))
from apply_logic import clear_markers
from resolve_api import get_resolve
p=RUNTIME/"pending.json"
if not p.exists():raise RuntimeError("没有最后一次分析记录。")
pending=json.loads(p.read_text(encoding="utf-8")); job=json.loads(Path(pending["job"]).read_text(encoding="utf-8")); print(json.dumps(clear_markers(get_resolve(),job,int(pending["candidate_index"])),ensure_ascii=False))
