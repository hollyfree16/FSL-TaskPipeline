import argparse
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Optional


def _run_single_feat(fsf_path: str) -> None:
    # FEAT expects an .fsf path
    subprocess.run(["feat", fsf_path], check=True)


def run_feat(
    fsf_paths: Iterable[str],
    *,
    max_workers: int = 10,
) -> None:
    """Run FSL FEAT for each FSF in fsf_paths in parallel."""
    fsf_list = [p for p in fsf_paths if p]
    if not fsf_list:
        return

    # ThreadPool is appropriate: each task is an external process.
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_run_single_feat, p): p for p in fsf_list}
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
) -> None:
    if write_commands:
        write_feat_commands(fsf_paths, output_file=write_commands)
    else:
        run_feat(fsf_paths, max_workers=max_workers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run (or emit) FSL FEAT commands for a set of FSF files.")
    parser.add_argument("fsf", nargs="+", help="One or more .fsf files to run with FEAT")
    parser.add_argument("--max_workers", type=int, default=10, help="Maximum number of parallel FEAT workers")
    parser.add_argument(
        "--write_commands",
        required=False,
        help="Instead of running FEAT, append 'feat <fsf>' commands to this file",
    )
    args = parser.parse_args()
    main(args.fsf, max_workers=args.max_workers, write_commands=args.write_commands)
