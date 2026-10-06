import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"backend"/"analyze_cli.py"
s=importlib.util.spec_from_file_location("a",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
r=m.normalize_result({"path":"x","bpm":120,"beats":[.5],"downbeats":[.5],"beat_positions":[1],"segments":[{"start":0,"end":3,"label":"intro"}]})
assert r["bpm"]==120 and r["segments"][0]["label"]=="intro"
print("backend normalize OK")
