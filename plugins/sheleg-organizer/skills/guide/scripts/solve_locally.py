# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Solve a Sheleg Organizer engine run on this computer.

Usage (uv provides Python and the engine's libraries):

    uv run --script solve_locally.py --ticket "<local.ticketUrl from engine_run>"

The ticket is a short-lived link the server hands out when an agent starts a
run with solveOn "caller". It names the run's input, where the result goes, and
the engine package to run, with its SHA-256. This script:

1. downloads the engine package once and keeps it in this computer's cache,
   checking its SHA-256, and refreshes it whenever the server names another one;
2. downloads the input, solves it with that engine, and uploads the result;
3. prints one line of JSON: {"ok": true, ...} or {"ok": false, "reason": ...}.

Nothing else leaves this computer, and the input and result are deleted from it
when the script ends. The agent then calls engine_submitResult with the run id.
When this script fails, the agent starts the run again with solveOn "server".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TICKET_VERSIONS = {"local-solve/1"}
INPUT_VERSIONS = {"engine-input/1"}
RESULT_VERSIONS = {"engine-result/1"}
MB = 1024 * 1024
# Time kept back before the hand-in deadline, so the agent can still hand the result in.
MARGIN_SECONDS = 60
# Engine packages kept in the cache besides the current one.
KEEP_PACKAGES = 2


class Failure(Exception):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


def say(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


def cache_dir() -> Path:
    override = os.environ.get("SHELEG_ORGANIZER_CACHE")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "sheleg-organizer" / "cache"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "sheleg-organizer"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "sheleg-organizer"


def fetch(url: str, limit: int, what: str) -> bytes:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "sheleg-organizer-local-solve/1"}), timeout=120) as res:
            data = res.read(limit + 1)
    except urllib.error.HTTPError as e:
        if e.code in (400, 401, 403, 404):
            raise Failure("link_expired", f"The {what} link was refused (HTTP {e.code}); it may have expired. Start a new run.") from e
        raise Failure("download_failed", f"Downloading the {what} failed: HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Failure("download_failed", f"Downloading the {what} failed: {e}") from e
    if len(data) > limit:
        raise Failure("too_large", f"The {what} is larger than {limit // MB} MB")
    return data


def upload(url: str, data: bytes) -> None:
    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={"Content-Type": "application/json", "x-upsert": "true", "User-Agent": "sheleg-organizer-local-solve/1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            res.read()
    except urllib.error.HTTPError as e:
        raise Failure("upload_failed", f"Uploading the result failed: HTTP {e.code} {e.read()[:300].decode('utf-8', 'replace')}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Failure("upload_failed", f"Uploading the result failed: {e}") from e


def engine_package(engine: dict) -> Path:
    """The engine package the server named, from the cache or downloaded once and checked."""
    sha = str(engine.get("sha256", ""))
    name = str(engine.get("file", ""))
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha) or not name.endswith(".whl") or "/" in name or "\\" in name:
        raise Failure("bad_ticket", "The ticket names no valid engine package")
    root = cache_dir() / "engine"
    target = root / sha / name
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == sha:
        return target
    say("Downloading the engine (once per engine version)...")
    data = fetch(str(engine["url"]), 50 * MB, "engine package")
    if hashlib.sha256(data).hexdigest() != sha:
        raise Failure("engine_checksum_mismatch", "The engine package does not match the checksum the server named; nothing was run")
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    partial.write_bytes(data)
    partial.replace(target)
    # Older engine packages are never run again once the server names a new one.
    others = sorted((p for p in root.iterdir() if p.is_dir() and p.name != sha), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in others[KEEP_PACKAGES:]:
        shutil.rmtree(old, ignore_errors=True)
    return target


def find_uv() -> str:
    uv = os.environ.get("UV") or shutil.which("uv")
    if not uv:
        raise Failure("uv_missing", "uv is not installed on this computer")
    return uv


def solve(ticket_url: str) -> dict:
    started = time.monotonic()
    ticket = json.loads(fetch(ticket_url, 1 * MB, "ticket"))
    run_id = ticket.get("runId")
    if ticket.get("version") not in TICKET_VERSIONS:
        raise Failure("plugin_outdated", f"This plugin does not know the ticket version {ticket.get('version')!r}; update the plugin")
    if ticket["input"].get("version") not in INPUT_VERSIONS or ticket["result"].get("version") not in RESULT_VERSIONS:
        raise Failure("plugin_outdated", "This plugin does not know the engine contract the server uses; update the plugin")
    deadline = datetime.fromisoformat(ticket["handInBy"].replace("Z", "+00:00"))
    budget = (deadline - datetime.now(timezone.utc)).total_seconds() - MARGIN_SECONDS
    if budget <= 0:
        raise Failure("too_late", "The run's time to hand in a result is up; start a new run")
    uv = find_uv()
    wheel = engine_package(ticket["engine"])
    module = str(ticket["engine"].get("module", ""))
    if not module.replace(".", "").replace("_", "").isalnum():
        raise Failure("bad_ticket", "The ticket names no valid engine module")
    with tempfile.TemporaryDirectory(prefix="sheleg-run-") as tmp:
        source = Path(tmp) / "input.json"
        target = Path(tmp) / "result.json"
        data = fetch(ticket["input"]["url"], 100 * MB, "input")
        if json.loads(data).get("version") != ticket["input"]["version"]:
            raise Failure("bad_input", "The input is not the version the ticket names")
        source.write_bytes(data)
        say("Solving on this computer...")
        env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME")}
        cmd = [uv, "run", "--no-project", "--quiet", "--python", "3.12", "--with", str(wheel), "python", "-m", module, str(source), str(target)]
        try:
            done = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=max(1, budget - (time.monotonic() - started)))
        except subprocess.TimeoutExpired as e:
            raise Failure("timeout", "The engine did not finish before the run's time to hand in a result") from e
        except OSError as e:
            raise Failure("engine_failed", f"The engine could not start: {e}") from e
        if done.returncode != 0 or not target.is_file():
            raise Failure("engine_failed", f"The engine failed (exit {done.returncode}): {done.stderr.strip()[-800:]}")
        result_bytes = target.read_bytes()
        result = json.loads(result_bytes)
        if result.get("version") != ticket["result"]["version"]:
            raise Failure("engine_mismatch", "The engine wrote another result version than the ticket names")
        if len(result_bytes) > int(ticket["result"].get("maxBytes", 20 * MB)):
            raise Failure("too_large", "The result is larger than the server takes")
        upload(ticket["result"]["uploadUrl"], result_bytes)
    return {
        "ok": True,
        "runId": run_id,
        "outcome": result.get("outcome"),
        "overall": (result.get("optimality") or {}).get("overall"),
        "proposal": len(result.get("proposal") or []),
        "seconds": round(time.monotonic() - started, 1),
        "next": f"Call engine_submitResult with runId {run_id}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve a Sheleg Organizer engine run on this computer.")
    parser.add_argument("--ticket", required=True, help="local.ticketUrl, as engine_run returned it")
    args = parser.parse_args()
    try:
        summary = solve(args.ticket)
    except Failure as f:
        print(json.dumps({"ok": False, "reason": f.reason, "message": f.message, "next": 'Start the run again with solveOn "server"'}))
        return 1
    except (KeyError, TypeError, ValueError) as e:
        print(json.dumps({"ok": False, "reason": "bad_ticket", "message": f"The ticket or a file it names is not readable: {e}", "next": 'Start the run again with solveOn "server"'}))
        return 1
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
