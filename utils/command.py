from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence, Union


def ensure_parent_dir(path: Union[str, Path]) -> None:
    p = Path(path)
    (p.parent if p.parent else Path('.')).mkdir(parents=True, exist_ok=True)


def append_log(log_file: Optional[Union[str, Path]], line: str) -> None:
    if not log_file:
        return
    ensure_parent_dir(log_file)
    ts = datetime.now().isoformat(timespec="seconds")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line.rstrip()}\n")


def run_cmd(
    cmd: Sequence[str],
    *,
    log_file: Optional[Union[str, Path]] = None,
    dry_run: bool = False,
    check: bool = True,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """Run a command safely (no shell), with optional logging and dry-run."""

    cmd_str = " ".join([_shell_quote(x) for x in cmd])
    append_log(log_file, f"$ {cmd_str}")
    if dry_run:
        # Mimic a successful process object
        return subprocess.CompletedProcess(args=list(cmd), returncode=0)

    try:
        return subprocess.run(
            list(cmd),
            check=check,
            cwd=str(cwd) if cwd is not None else None,
            env=env,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        # Always log stdout/stderr on failure.
        if e.stdout:
            append_log(log_file, f"stdout: {e.stdout.strip()}")
        if e.stderr:
            append_log(log_file, f"stderr: {e.stderr.strip()}")
        raise


def _shell_quote(s: str) -> str:
    # Simple quoting for logs only.
    if not s:
        return "''"
    if any(ch.isspace() or ch in "\\\"'`$" for ch in s):
        return "'" + s.replace("'", "'\\''") + "'"
    return s
