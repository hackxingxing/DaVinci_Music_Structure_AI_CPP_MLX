from __future__ import annotations
import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path
SCRIPTING_ROOT = Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting")
MODULES = SCRIPTING_ROOT / "Modules"
FUSIONSCRIPT = Path("/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so")

def configure_environment() -> None:
    if str(MODULES) not in sys.path:
        sys.path.insert(0, str(MODULES))
    os.environ.setdefault("RESOLVE_SCRIPT_API", str(SCRIPTING_ROOT))
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", str(FUSIONSCRIPT))

def _load_fusionscript_direct():
    if not FUSIONSCRIPT.exists():
        raise FileNotFoundError(f"Resolve scripting library not found: {FUSIONSCRIPT}")
    loader = importlib.machinery.ExtensionFileLoader("fusionscript", str(FUSIONSCRIPT))
    spec = importlib.util.spec_from_loader("fusionscript", loader)
    if spec is None:
        raise ImportError("Could not create fusionscript module spec")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

def get_resolve():
    configure_environment()
    first_error = None
    try:
        import DaVinciResolveScript as dvr_script
        resolve = dvr_script.scriptapp("Resolve")
        if resolve:
            return resolve
    except Exception as exc:
        first_error = exc
    try:
        fusionscript = _load_fusionscript_direct()
        resolve = fusionscript.scriptapp("Resolve")
        if resolve:
            return resolve
    except Exception as exc:
        first_error = RuntimeError(f"official loader: {first_error}; direct loader: {exc}") if first_error else exc
    raise RuntimeError(
        "无法从外部连接 DaVinci Resolve。请确认 Resolve 已打开；若要自动写回 Marker，"
        "在 Resolve Preferences → System → General 中把 External Scripting Using 设为 Local。"
        + (f"\n详细错误：{first_error}" if first_error else "")
    )
