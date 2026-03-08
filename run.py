#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import List

ROOT_DIR = Path(__file__).resolve().parent
ML_SERVICE_DIR = ROOT_DIR / "ml-service"
CLIENT_DIR = ROOT_DIR / "client"


def _project_python() -> Path:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return venv_python
    return Path(sys.executable)


def _maybe_reexec_into_project_python() -> None:
    venv_dir = ROOT_DIR / ".venv"
    target = _project_python()
    if not target.exists() or not venv_dir.exists():
        return

    current_prefix = Path(sys.prefix).resolve()
    if current_prefix != venv_dir.resolve():
        os.execv(str(target), [str(target), str(Path(__file__).resolve()), *sys.argv[1:]])


def _load_reporting_module():
    if str(ML_SERVICE_DIR) not in sys.path:
        sys.path.insert(0, str(ML_SERVICE_DIR))
    from reporting import generate_gold_report_bundle

    return generate_gold_report_bundle


def _wait_for_shutdown(processes: List[subprocess.Popen]) -> int:
    try:
        while True:
            for process in processes:
                code = process.poll()
                if code is not None:
                    return code
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        for process in reversed(processes):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


def _run_gui(args: argparse.Namespace) -> int:
    backend_cmd = [
        str(_project_python()),
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        args.host,
        "--port",
        str(args.backend_port),
    ]
    frontend_cmd = [
        "npm",
        "run",
        "dev",
        "--",
        "--host",
        args.host,
        "--port",
        str(args.frontend_port),
    ]

    backend = subprocess.Popen(backend_cmd, cwd=ML_SERVICE_DIR, start_new_session=True)
    time.sleep(2)
    frontend = subprocess.Popen(frontend_cmd, cwd=CLIENT_DIR, start_new_session=True)

    url = f"http://{args.host}:{args.frontend_port}/"
    print(f"GUI mode running: {url}")
    if not args.no_browser:
        time.sleep(2)
        webbrowser.open(url)

    code = _wait_for_shutdown([backend, frontend])

    if code == 0:
        return 0
    if code < 0:
        return 128 + abs(code)
    return code


def _run_bot_mode(args: argparse.Namespace) -> int:
    generate_gold_report_bundle = _load_reporting_module()
    manifest = generate_gold_report_bundle(
        output_dir=args.bot_output_dir,
        source=args.report_source,
        horizon=args.horizon,
        lookback=args.lookback,
        compare_days=args.compare_days,
        session_days=args.session_days,
        session_period=args.session_period,
    )
    output_path = Path(args.bot_output_dir).expanduser().resolve()
    print(f"Bot report generated at: {output_path}")
    print(f"Manifest: {output_path / manifest['files']['manifest_json']}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stock Prediction launcher: GUI by default, bot report mode when output dir is provided.",
    )
    parser.add_argument("--bot-output-dir", help="Directory where the bot-readable report bundle will be written")
    parser.add_argument("--report-source", default="SHFE_AU_MAIN", help="Gold source used in bot mode")
    parser.add_argument("--horizon", type=int, default=5, help="Forecast horizon for bot mode")
    parser.add_argument("--lookback", type=int, default=240, help="Training lookback window for bot mode")
    parser.add_argument("--compare-days", type=int, default=180, help="Compare chart lookback in days")
    parser.add_argument("--session-days", type=int, default=5, help="Session chart lookback in days")
    parser.add_argument(
        "--session-period",
        default="15min",
        choices=["5min", "15min", "30min", "60min"],
        help="Session chart granularity for bot mode",
    )
    parser.add_argument("--host", default="127.0.0.1", help="GUI mode host")
    parser.add_argument("--backend-port", type=int, default=8000, help="GUI mode backend port")
    parser.add_argument("--frontend-port", type=int, default=3000, help="GUI mode frontend port")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser in GUI mode")
    return parser


def main() -> int:
    _maybe_reexec_into_project_python()
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    parser = _build_parser()
    args = parser.parse_args()

    if args.bot_output_dir:
        return _run_bot_mode(args)
    return _run_gui(args)


if __name__ == "__main__":
    raise SystemExit(main())
