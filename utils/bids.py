from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional, Union


# Match entities delimited by start-of-string, '/', or '_' (common in BIDS filenames).
_ENTITY_PATTERNS = {
    "subject": re.compile(r"(?:^|[/_])sub-([A-Za-z0-9]+)(?=$|[/_])"),
    "session": re.compile(r"(?:^|[/_])ses-([A-Za-z0-9]+)(?=$|[/_])"),
    "task": re.compile(r"(?:^|[/_])task-([A-Za-z0-9]+)(?=$|[/_])"),
    "run": re.compile(r"(?:^|[/_])run-([0-9]+)(?=$|[/_])"),
}


def parse_bids_entities(path: Union[str, Path]) -> Dict[str, Any]:
    """Extract common BIDS entities from a path or filename.

    Returns keys: subject, session, task, run (run is int if present).
    Values are None if not found.
    """
    s = str(path)
    out: Dict[str, Any] = {"subject": None, "session": None, "task": None, "run": None}
    for key, pat in _ENTITY_PATTERNS.items():
        m = pat.search(s)
        if not m:
            continue
        val = m.group(1)
        if key == "run":
            try:
                out[key] = int(val)
            except ValueError:
                out[key] = None
        else:
            out[key] = val
    return out


def match_filters(
    entities: Dict[str, Any],
    *,
    subject: Optional[str] = None,
    task_filters: Optional[list[str]] = None,
    run_filters: Optional[list[Optional[int]]] = None,
    session: Optional[str] = None,
) -> bool:
    if subject and entities.get("subject") != subject.replace("sub-", ""):
        return False
    if session and entities.get("session") != session.replace("ses-", ""):
        return False
    if task_filters:
        t = entities.get("task")
        if t is None or t not in task_filters:
            return False
    if run_filters is not None and len(run_filters) > 0:
        r = entities.get("run")
        want_no_run = any(x is None for x in run_filters)
        want_numeric = [x for x in run_filters if x is not None]
        if r is None:
            return want_no_run
        return r in want_numeric
    return True
