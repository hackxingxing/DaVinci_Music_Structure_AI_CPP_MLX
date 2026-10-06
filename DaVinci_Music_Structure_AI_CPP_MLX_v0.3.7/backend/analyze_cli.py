#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path

APP_SUPPORT = Path.home() / "Library/Application Support/MusicStructureAI_CPP"
LOG_DIR = Path.home() / "Library/Logs/MusicStructureAI_CPP"
ANALYZE_LOG = LOG_DIR / "analyze.log"
DEFAULT_WEIGHTS_DIR = APP_SUPPORT / "mlx-weights"


def find_ffmpeg():
    for p in (shutil.which("ffmpeg"), "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        if p and Path(p).exists():
            return str(p)
    return None


def find_allin1_cli():
    local = Path(sys.executable).parent / "allin1-mlx"
    return str(local) if local.exists() else shutil.which("allin1-mlx")


def append_log(text: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with ANALYZE_LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n===== {stamp} =====\n{text.rstrip()}\n")


def run(cmd, env=None, stage="command"):
    printable = " ".join(subprocess.list2cmdline([str(x)]) for x in cmd)
    append_log(f"[{stage}] $ {printable}")
    p = subprocess.run(
        [str(x) for x in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    append_log(f"[{stage}] exit={p.returncode}\n{p.stdout}")
    if p.returncode != 0:
        raise RuntimeError(p.stdout[-12000:])
    return p.stdout


def normalize_result(raw):
    out = {
        "path": str(raw.get("path", "")),
        "bpm": raw.get("bpm", 0),
        "beats": [float(x) for x in raw.get("beats", [])],
        "downbeats": [float(x) for x in raw.get("downbeats", [])],
        "beat_positions": [int(x) for x in raw.get("beat_positions", [])],
        "segments": [],
    }
    for seg in raw.get("segments", []) or []:
        if isinstance(seg, dict):
            out["segments"].append(
                {
                    "start": float(seg.get("start", 0.0)),
                    "end": float(seg.get("end", 0.0)),
                    "label": str(seg.get("label", "")),
                }
            )
        else:
            out["segments"].append(
                {
                    "start": float(getattr(seg, "start", 0.0)),
                    "end": float(getattr(seg, "end", 0.0)),
                    "label": str(getattr(seg, "label", "")),
                }
            )
    return out


def weight_files(weights_dir: Path):
    files = []
    for fold in range(8):
        files.append(weights_dir / f"harmonix-fold{fold}_mlx.npz")
        files.append(weights_dir / f"harmonix-fold{fold}_mlx.yaml")
    return files


def validate_weights(weights_dir: Path):
    missing = []
    invalid = []
    for p in weight_files(weights_dir):
        if not p.exists():
            missing.append(str(p))
            continue
        size = p.stat().st_size
        if p.suffix == ".npz" and (size < 1024 or not zipfile.is_zipfile(p)):
            invalid.append(f"{p} ({size} bytes / invalid npz)")
        if p.suffix == ".yaml" and size < 20:
            invalid.append(f"{p} ({size} bytes)")
    if missing or invalid:
        details = []
        if missing:
            details.append("缺失权重：\n" + "\n".join(missing[:8]))
        if invalid:
            details.append("权重文件异常：\n" + "\n".join(invalid[:8]))
        raise RuntimeError(
            "MLX 模型权重不完整。请重新运行 v0.3.4 install.command。\n"
            + "\n".join(details)
        )


def self_test():
    cli = find_allin1_cli()
    ffmpeg = find_ffmpeg()
    weights_ok = False
    try:
        validate_weights(DEFAULT_WEIGHTS_DIR)
        weights_ok = True
    except Exception:
        pass
    info = {
        "ok": bool(cli and ffmpeg and weights_ok),
        "python": sys.version.split()[0],
        "arch": platform.machine(),
        "ffmpeg": ffmpeg,
        "allin1_mlx_cli": cli,
        "weights_dir": str(DEFAULT_WEIGHTS_DIR),
        "weights_ok": weights_ok,
        "analyze_log": str(ANALYZE_LOG),
    }
    print(json.dumps(info, ensure_ascii=False))
    return 0 if info["ok"] else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job")
    ap.add_argument("--candidate-index", type=int, default=0)
    ap.add_argument("--output")
    ap.add_argument("--model", default="harmonix-all")
    ap.add_argument("--weights-dir", default=str(DEFAULT_WEIGHTS_DIR))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.job or not args.output:
        ap.error("--job and --output are required")

    weights_dir = Path(args.weights_dir).expanduser().resolve()
    validate_weights(weights_dir)

    job_path = Path(args.job).expanduser().resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    candidates = job.get("candidates", [])
    if not (0 <= args.candidate_index < len(candidates)):
        raise RuntimeError("candidate index out of range")

    c = candidates[args.candidate_index]
    source = Path(c["path"]).expanduser().resolve()
    start = max(0.0, float(c.get("source_start_seconds", 0.0)))
    end = max(start, float(c.get("source_end_seconds", start)))
    duration = end - start
    if duration <= 0.05:
        raise RuntimeError("Resolve did not provide a usable source duration for this audio clip")
    if not source.exists():
        raise FileNotFoundError(source)

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        print(f"CACHE_HIT {output}")
        return 0

    ffmpeg = find_ffmpeg()
    cli = find_allin1_cli()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")
    if not cli:
        raise RuntimeError("allin1-mlx CLI not found in the plugin virtual environment")

    started = time.time()
    append_log(
        "ANALYSIS START\n"
        f"source={source}\nstart={start:.6f}\nduration={duration:.6f}\n"
        f"model={args.model}\nweights_dir={weights_dir}\n"
        f"python={sys.executable}\ncli={cli}\nffmpeg={ffmpeg}"
    )

    with tempfile.TemporaryDirectory(prefix="msai-cpp-") as td:
        td = Path(td)
        wav = td / "selection.wav"
        struct_dir = td / "struct"
        struct_dir.mkdir(parents=True, exist_ok=True)

        pre_roll = min(10.0, start)
        coarse = start - pre_roll
        precise = pre_roll
        run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{coarse:.6f}",
                "-i",
                str(source),
                "-ss",
                f"{precise:.6f}",
                "-t",
                f"{duration:.6f}",
                "-vn",
                "-ac",
                "2",
                "-ar",
                "44100",
                "-c:a",
                "pcm_s16le",
                str(wav),
            ],
            stage="ffmpeg",
        )

        env = os.environ.copy()
        env["PATH"] = (
            "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:"
            + env.get("PATH", "")
        )
        cli_out = run(
            [
                cli,
                str(wav),
                "--out-dir",
                str(struct_dir),
                "--model",
                args.model,
                "--spec-backend",
                "mlx_fast",
                "--mlx-weights-dir",
                str(weights_dir),
            ],
            env=env,
            stage="allin1-mlx",
        )

        files = [p for p in struct_dir.glob("*.json") if "timing" not in p.name.lower()]
        if not files:
            raise RuntimeError("allin1-mlx did not produce a JSON result\n" + cli_out[-4000:])

        result_file = max(files, key=lambda p: p.stat().st_mtime_ns)
        raw = json.loads(result_file.read_text(encoding="utf-8"))
        data = normalize_result(raw)
        data.update(
            {
                "source_path": str(source),
                "source_start_seconds": start,
                "source_duration_seconds": duration,
                "analyzer_backend": "mlx",
                "analyzer": "ssmall256/all-in-one-mlx",
                "model": args.model,
                "weights_dir": str(weights_dir),
                "analysis_seconds": round(time.time() - started, 3),
            }
        )
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        append_log(f"ANALYSIS OK output={output} seconds={data['analysis_seconds']}")
        print(f"OK {output}")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        tb = traceback.format_exc()
        append_log("ANALYSIS FAILED\n" + tb)
        # Keep GUI error short; complete traceback is in analyze.log.
        message = str(exc).strip().splitlines()
        tail = " | ".join(message[-4:]) if message else exc.__class__.__name__
        print(
            f"ERROR: {tail}\n完整日志：{ANALYZE_LOG}",
            file=sys.stderr,
        )
        raise SystemExit(1)
