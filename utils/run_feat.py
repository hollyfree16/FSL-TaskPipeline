import argparse
import os
import re
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Optional


from .command import run_cmd


_OUTPUTDIR_RE = re.compile(r"^\s*set\s+fmri\(outputdir\)\s+\"?([^\"\n]+)\"?\s*$")


def feat_outputdir_from_fsf(fsf_path: str) -> str | None:
    try:
        with open(fsf_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = _OUTPUTDIR_RE.match(line)
                if m:
                    return m.group(1)
    except FileNotFoundError:
        return None
    return None


def feat_is_complete(outputdir: str) -> bool:
    p = Path(outputdir)
    if not p.exists() or not p.is_dir():
        return False
    # Heuristic: a completed FEAT directory typically has these.
    if not (p / "design.fsf").exists():
        return False
    if not (p / "stats").exists():
        return False
    # filtered_func_data.nii.gz is created for standard first-level analyses
    if (p / "filtered_func_data.nii.gz").exists():
        return True
    # Some analyses may not create filtered_func_data; fallback to report
    return (p / "report.html").exists()


def _run_single_feat(
    fsf_path: str,
    *,
    log_file=None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    outdir = feat_outputdir_from_fsf(fsf_path)
    if outdir and feat_is_complete(outdir) and not force:
        return
    run_cmd(["feat", fsf_path], log_file=log_file, dry_run=dry_run, check=True)


def run_feat(
    fsf_paths: Iterable[str],
    *,
    max_workers: int = 10,
    log_file: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """Run FSL FEAT for each FSF in fsf_paths in parallel."""
    fsf_list = [p for p in fsf_paths if p]
    if not fsf_list:
        return

    # ThreadPool is appropriate: each task is an external process.
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_run_single_feat, p, log_file=log_file, dry_run=dry_run, force=force): p for p in fsf_list}
        for fut in as_completed(futures):
            fsf = futures[fut]
            try:
                fut.result()
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"FEAT failed for {fsf}: {e}") from e


def write_feat_commands(
    fsf_paths: Iterable[str],
    *,
    output_file: str,
) -> None:
    """Append 'feat <fsf>' commands to output_file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_file)) or ".", exist_ok=True)
    with open(output_file, "a") as f:
        for p in fsf_paths:
            if p:
                f.write(f"feat {p}\n")


def main(
    fsf_paths: List[str],
    *,
    max_workers: int = 10,
    write_commands: Optional[str] = None,
    log_file: Optional[str] = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    if write_commands:
        write_feat_commands(fsf_paths, output_file=write_commands)
    else:
        run_feat(fsf_paths, max_workers=max_workers, log_file=log_file, dry_run=dry_run, force=force)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run (or emit) FSL FEAT commands for a set of FSF files.")
    parser.add_argument("fsf", nargs="+", help="One or more .fsf files to run with FEAT")
    parser.add_argument("--max_workers", type=int, default=10, help="Maximum number of parallel FEAT workers")
    parser.add_argument("--log_file", required=False, help="Optional log file to append commands and failures")
    parser.add_argument("--dry_run", action="store_true", help="Print/log commands but do not execute")
    parser.add_argument("--force", action="store_true", help="Re-run FEAT even if output appears complete")
    parser.add_argument(
        "--write_commands",
        required=False,
        help="Instead of running FEAT, append 'feat <fsf>' commands to this file",
    )
    args = parser.parse_args()
    main(
        args.fsf,
        max_workers=args.max_workers,
        write_commands=args.write_commands,
        log_file=args.log_file,
        dry_run=args.dry_run,
        force=args.force,
    )
