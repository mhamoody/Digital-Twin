"""Manage one parallel Lobot React/API process, without touching existing services.

Linux /proc start-time + command checks and pidfd signalling prevent a stale
PID file from stopping an unrelated process. No migrations, model or worker launch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request

PORT = 8502
PREFIX = "/user/group-digi2026-g12/proxy/8502/"


def process_identity(pid: int):
    try:
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        if stat[0] == "Z":
            return None
        command = Path(f"/proc/{pid}/cmdline").read_bytes()
        return {"start_ticks": stat[19], "command_hash": hashlib.sha256(command).hexdigest()}
    except (FileNotFoundError, ProcessLookupError):
        return None


def matches(record):
    identity = process_identity(record["pid"])
    return identity is not None and all(identity[k] == record[k] for k in identity)


def started_identity(process, command):
    """Wait for exec to publish the child argv before recording its identity.

    Immediately after Popen, /proc can still expose the parent's pre-exec argv.
    Never persist that transient hash or adopt an exited/reused child PID.
    """
    expected = hashlib.sha256(b"\0".join(os.fsencode(part) for part in command) + b"\0").hexdigest()
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("React process exited at startup. Inspect var/log/react-api.log.")
        identity = process_identity(process.pid)
        if identity and identity["command_hash"] == expected:
            if process.poll() is None:
                return identity
            break
        time.sleep(.05)
    raise RuntimeError("React child did not establish its expected command identity; inspect var/log/react-api.log.")


def stop_owned(record):
    if not matches(record):
        raise RuntimeError("Saved PID does not match the React process. Refusing to signal it.")
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        raise RuntimeError("Safe pidfd signalling unavailable. Operator intervention required.")
    fd = os.pidfd_open(record["pid"])
    try:
        if not matches(record):
            raise RuntimeError("Process identity changed. No signal sent.")
        signal.pidfd_send_signal(fd, signal.SIGTERM)
    finally:
        os.close(fd)
    for _ in range(50):
        if not matches(record):
            return
        time.sleep(.1)
    raise RuntimeError("React is still shutting down. No force kill was sent; check status/logs.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("start", "status", "stop"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--shared-root", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "linux":
        raise RuntimeError("This helper manages the Linux Lobot process only.")
    import fcntl

    root, shared = args.root.resolve(strict=True), args.shared_root.resolve(strict=True)
    run, logs = shared / "var/run", shared / "var/log"
    run.mkdir(parents=True, exist_ok=True, mode=0o700)
    logs.mkdir(parents=True, exist_ok=True, mode=0o700)
    pid_file = run / "react-api.json"
    with (run / "react-api.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = json.loads(pid_file.read_text()) if pid_file.exists() else None
        if record and (record.get("root") != str(root) or record.get("shared") != str(shared)):
            raise RuntimeError("React record belongs to another worktree. Use that worktree's helper.")
        alive = record is not None and matches(record)
        if args.operation == "status":
            print(json.dumps({"running": alive, "pid": record["pid"] if alive else None,
                              "url": "https://lobot.cs.queensu.ca" + PREFIX,
                              "log": str(logs / "react-api.log")}))
            return
        if args.operation == "stop":
            if not alive:
                print("React is not running under its recorded identity; no process was signalled.")
                return
            stop_owned(record)
            print("Only the parallel React/API process was stopped. Streamlit and the analysis worker are unchanged.")
            return
        if alive:
            print("Parallel React/API is already running. No process changed.")
            return
        if record and process_identity(record["pid"]) is not None:
            raise RuntimeError("Recorded PID now belongs to a different process. Refusing restart; inspect the stale record.")
        dist = root / "frontend/dist"
        if not (dist / "index.html").is_file():
            raise RuntimeError("Build or transfer frontend/dist before starting React.")
        if not Path(os.environ["DIGITAL_TWIN_AUTH_FILE"]).is_file():
            raise RuntimeError("Existing instructor accounts are unavailable.")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", PORT))
        command = [sys.executable, "-m", "uvicorn", "digital_twin.api.app:app",
                   "--app-dir", str(root / "src"), "--host", "127.0.0.1", "--port", str(PORT),
                   "--workers", "1", "--root-path", PREFIX.rstrip("/")]
        # Environment values never enter the process command line or printed output.
        with (logs / "react-api.log").open("ab") as output:
            process = subprocess.Popen(command, cwd=shared, stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        identity = started_identity(process, command)
        record = {"pid": process.pid, **identity, "root": str(root), "shared": str(shared)}
        temporary = run / "react-api.json.new"
        temporary.write_text(json.dumps(record))
        temporary.chmod(0o600)
        temporary.replace(pid_file)
        ready = False
        for _ in range(30):
            if not matches(record):
                break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health/ready", timeout=1) as response:
                    ready = response.status == 200
            except OSError:
                pass
            if ready:
                break
            time.sleep(.5)
        if not ready:
            if matches(record):
                stop_owned(record)
            raise RuntimeError("React readiness failed. Inspect var/log/react-api.log; original services were not touched.")
        print("Parallel React/API ready: https://lobot.cs.queensu.ca" + PREFIX)
        print("Same course database and instructor accounts; no new analysis worker was started.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        # Never dump environment, HTTP response contents or account records.
        print(f"React deployment stopped: {type(error).__name__}. {error}", file=sys.stderr)
        sys.exit(1)
