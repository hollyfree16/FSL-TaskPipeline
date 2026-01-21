#!/usr/bin/env python3

import argparse
import time
import resource  # Unix-specific; consider psutil for Windows compatibility
import psutil  # To track child processes
import os
import re

from utils.run_motion_outliers import main as run_motion_outliers_main
from utils.run_synthstrip import main as run_synthstrip_main
from utils.extract_parameters import main as extract_parameters_main
from utils.generate_design_files import main as generate_design_files_main
from utils.generate_higher_level_feat_files import main as generate_higher_level_feat_files_main
from utils.run_feat import main as run_feat_main
from utils.command import append_log


def _parse_runs(run_args):
    """Parse --run arguments.

    Supports integer runs (e.g., 1 2) and the special token 'none' to indicate
    that the BOLD filename does not contain a run label.

    Returns a list where None indicates "no run label".
    """
    if not run_args:
        raise ValueError("--run is required")

    normalized = [str(r).strip().lower() for r in run_args]
    if "none" in normalized:
        if len(normalized) != 1:
            raise ValueError("--run none cannot be combined with numeric runs")
        return [None]

    runs = []
    for r in normalized:
        try:
            runs.append(int(r))
        except ValueError as e:
            raise ValueError(f"Invalid --run value: {r}") from e
    return runs

def get_total_memory_usage():
    """Get peak memory usage including child processes."""
    process = psutil.Process()
    mem_usage = process.memory_info().rss  # Resident Set Size (bytes)
    for child in process.children(recursive=True):
        mem_usage += child.memory_info().rss
    return mem_usage / (1024 * 1024)  # Convert to MB

def get_total_cpu_time():
    """Get CPU time usage including child processes."""
    process = psutil.Process()
    cpu_time = process.cpu_times().user + process.cpu_times().system
    for child in process.children(recursive=True):
        cpu_time += child.cpu_times().user + child.cpu_times().system
    return cpu_time

def _normalize_subjects(subjects_arg, input_directory):
    """Normalize --subjects.

    Returns None to indicate 'all subjects'. Otherwise returns a list of subject IDs.
    Accepts: None, a list of strings from argparse, a single comma-separated string, or a path to a text file.
    """
    if not subjects_arg:
        return None
    # argparse with nargs='+' returns a list; accept also a single string.
    if isinstance(subjects_arg, str):
        tokens = [subjects_arg]
    else:
        tokens = list(subjects_arg)
    # If a single token is a file path, read it.
    if len(tokens) == 1 and os.path.exists(tokens[0]) and os.path.isfile(tokens[0]):
        with open(tokens[0], 'r') as f:
            content = f.read().strip()
        raw = re.split(r'[\n,]+', content)
        subs = [s.strip() for s in raw if s.strip()]
        return subs or None
    # Otherwise split each token on commas.
    subs = []
    for t in tokens:
        subs.extend([s.strip() for s in t.split(',') if s.strip()])
    return subs or None


def main():
    parser = argparse.ArgumentParser(description="Wrapper script to run all FSL Task Pipeline steps.")

    # Core arguments
    parser.add_argument("--input_directory", required=True, help="Input BIDS directory.")
    parser.add_argument("--output_directory", required=True, help="Output directory.")
    parser.add_argument("--fsf_template", required=True, help="Path to the .fsf template file.")
    parser.add_argument("--task", nargs='+', required=True, help="One or more task names (e.g., --task hand language).")
    parser.add_argument(
        "--run",
        nargs='+',
        required=True,
        help=(
            "Run numbers to process (e.g., --run 1 2). Use '--run none' when the BOLD filename does not "
            "contain a run label (e.g., sub-XXX_ses-YYY_task-T_bold.nii.gz)."
        ),
    )
    parser.add_argument("--subjects", nargs="+", required=False, help=("One or more subject IDs (e.g., sub-001 sub-002) OR a path to a text file containing subjects (comma/newline-separated). If omitted, process all subjects found in the input directory."))
    parser.add_argument("--custom_block", nargs='*', default=[], help="Custom block inputs (optional).")
    parser.add_argument("--write_commands", required=False, help="Instead of running commands locally, write all commands to a text file for HPC execution.")
    parser.add_argument("--max_workers", type=int, default=10, help="Maximum number of parallel workers.")
    parser.add_argument("--higher_level_fsf_template", required=False, help="Path to the higher-level .fsf template file.")
    parser.add_argument("--dry_run", action="store_true", help="Print/log commands but do not execute external tools")
    parser.add_argument("--force", action="store_true", help="Re-run steps even if outputs already exist")

    # New flag to track resources
    parser.add_argument("--track_resources", action="store_true", help="Track system resources and runtime usage.")

    args = parser.parse_args()

    runs = _parse_runs(args.run)

    subjects_list = _normalize_subjects(args.subjects, args.input_directory)

    # Determine subjects to process.
    if subjects_list is not None:
        subject_iter = subjects_list
    else:
        # Default: process every subject directory under input_directory.
        subject_iter = sorted(
            [d for d in os.listdir(args.input_directory) if d.startswith("sub-") and os.path.isdir(os.path.join(args.input_directory, d))]
        )


    if args.track_resources:
        start_time = time.time()
        start_cpu_time = get_total_cpu_time()

    # Run pipeline steps
    # Preprocessing steps should run once, even if multiple tasks are requested.

    for subject in subject_iter:
        subject_arg = subject
        log_file = os.path.join(args.output_directory, "logs", subject_arg, "pipeline.log")
        append_log(log_file, f"=== Begin subject {subject_arg} ===")
        # Preprocessing runs once per subject (not once per task).
        run_motion_outliers_main(
            args.input_directory,
            args.output_directory,
            subject_arg,
            args.max_workers,
            args.task,
            runs,
            log_file=log_file,
            dry_run=args.dry_run,
            force=args.force,
        )
        run_synthstrip_main(
            args.input_directory,
            args.output_directory,
            subject_arg,
            args.max_workers,
            args.task,
            runs,
            log_file=log_file,
            dry_run=args.dry_run,
            force=args.force,
        )
        extract_parameters_main(args.input_directory, args.output_directory, subject_arg, args.task, runs)
    
        first_level_fsfs = []
        for task in args.task:
            first_level_fsfs.extend(
                generate_design_files_main(
                    fsf_template=args.fsf_template,
                    output_directory=args.output_directory,
                    input_directory=args.input_directory,
                    task=task,
                    custom_block=args.custom_block,
                    subjects=subject_arg,
                    runs=runs,
                )
            )
    
        # Run FEAT or emit FEAT commands for first level.
        run_feat_main(
            first_level_fsfs,
            max_workers=args.max_workers,
            write_commands=args.write_commands,
            log_file=log_file,
            dry_run=args.dry_run,
            force=args.force,
        )
        if args.higher_level_fsf_template:
            analysis_blocks = args.custom_block if args.custom_block else ["standard"]
    
            # Pair whichever runs were passed. If more than two, pair the first two.
            # Higher-level analysis is only meaningful for numeric runs.
            numeric_runs = [r for r in runs if r is not None]
            run_pair = tuple(numeric_runs[:2]) if len(numeric_runs) >= 2 else None
    
            higher_level_fsfs_all = []
            for block in analysis_blocks:
                first_level_root = os.path.join(
                    args.output_directory,
                    "fsl_feat_v6.0.7.4",
                    block,
                )
                higher_level_design_dir = os.path.join(
                    args.output_directory,
                    "fsl_feat_v6.0.7.4",
                    "higher_level_designs",
                    block,
                )
                higher_level_output_dir = os.path.join(
                    args.output_directory,
                    "fsl_feat_v6.0.7.4",
                    "higher_level_outputs",
                    block,
                )
                higher_level_fsfs = []
                if run_pair is not None:
                    higher_level_fsfs = generate_higher_level_feat_files_main(
                        input_directory=first_level_root,
                        template_file=args.higher_level_fsf_template,
                        design_output_dir=higher_level_design_dir,
                        feat_output_dir=higher_level_output_dir,
                        run_pair=run_pair,
                        subjects=subject_arg,
                        task_filters=args.task,
                    )
    
                if higher_level_fsfs:
                    higher_level_fsfs_all.extend(higher_level_fsfs)
    
            # Run FEAT or emit FEAT commands for higher level.
            run_feat_main(
                higher_level_fsfs_all,
                max_workers=args.max_workers,
                write_commands=args.write_commands,
                log_file=log_file,
                dry_run=args.dry_run,
                force=args.force,
            )

        append_log(log_file, f"=== End subject {subject_arg} ===")
    
    if args.track_resources:
        end_time = time.time()
        end_cpu_time = get_total_cpu_time()
        peak_memory = get_total_memory_usage()

        runtime = end_time - start_time
        cpu_time_used = end_cpu_time - start_cpu_time
        # Get resource usage for the current process.
        usage = resource.getrusage(resource.RUSAGE_SELF)

        print("\n--- Resource Usage Summary ---")
        print(f"Total runtime: {runtime:.2f} seconds")
        print(f"Total CPU time used: {cpu_time_used:.2f} seconds")
        print(f"Peak memory usage: {peak_memory:.2f} MB")
        print(f"Maximum resident set size (main process): {usage.ru_maxrss / 1024:.2f} MB")  # Convert KB to MB
        print("--------------------------------")

    print("All pipeline steps completed successfully!")

if __name__ == "__main__":
    main()