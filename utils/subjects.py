from __future__ import annotations

import os
import re
from typing import Iterable


def parse_subjects_arg(subjects_arg: str | Iterable[str] | None) -> list[str] | None:
    """Normalize subject input into a flat subject-id list.

    Accepts:
    - ``None`` -> ``None`` (caller can interpret as "all subjects")
    - a list/tuple/set of tokens
    - a comma-separated string
    - a path to a file containing comma/newline-separated subjects
    """
    if not subjects_arg:
        return None

    if isinstance(subjects_arg, str):
        tokens = [subjects_arg]
    else:
        tokens = [str(s).strip() for s in subjects_arg if str(s).strip()]

    if len(tokens) == 1 and os.path.isfile(tokens[0]):
        with open(tokens[0], "r", encoding="utf-8") as f:
            raw = f.read().strip()
        subs = [s.strip() for s in re.split(r"[\n,]+", raw) if s.strip()]
        return subs or None

    subs: list[str] = []
    for t in tokens:
        subs.extend([s.strip() for s in t.split(",") if s.strip()])
    return subs or None
