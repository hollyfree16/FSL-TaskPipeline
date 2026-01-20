#!/usr/bin/env python3

import argparse
import time
import resource  # Unix-specific; consider psutil for Windows compatibility
import psutil  # To track child processes
import os

from utils.run_motion_outliers import main as run_motion_outliers_main
from utils.run_synthstrip import main as run_synthstrip_main
from utils.extract_parameters import main as extract_parameters_main
from utils.generate_design_files import main as generate_design_files_main
from utils.generate_higher_level_feat_files import main as generate_higher_level_feat_files_main
from utils.run_feat import main as run_feat_main

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

def main():
    parser = argparse.ArgumentParser(description="Wrapper script to run all FSL Task Pipeline steps.")

    # Core arguments
    parser.add_argument("--input_directory", required=True, help="Input BIDS directory.")
    parser.add_argument("--output_directory", required=True, help="Output directory.")
    parser.add_argument("--fsf_template", required=True, help="Path to the .fsf template file.")
    parser.add_argument("--task", required=True, help="Task name (e.g., hand).")
    parser.add_argument("--run", nargs='+', type=int, required=True, help="Run numbers to process (e.g., --run 1 2).")
    parser.add_argument("--subjects", required=False, help="List of subjects to process. Can be passed directly as comma-separated values or a text file. Default will process entire directory.")
    parser.add_argument("--custom_block", nargs='*', default=[], help="Custom block inputs (optional).")
    parser.add_argument("--write_commands", required=False, help="Instead of running commands locally, write all commands to a text file for HPC execution.")
    parser.add_argument("--max_workers", type=int, default=10, help="Maximum number of parallel workers.")
    parser.add_argument("--higher_level_fsf_template", required=False, help="Path to the higher-level .fsf template file.")

    # New flag to track resources
    parser.add_argument("--track_resources", action="store_true", help="Track system resources and runtime usage.")

    args = parser.parse_args()

    if args.track_resources:
        start_time = time.time()
        start_cpu_time = get_total_cpu_time()

    # Run pipeline steps
    run_motion_outliers_main(args.input_directory, args.output_directory, args.subjects, args.max_workers, args.task, args.run)
    run_synthstrip_main(args.input_directory, args.output_directory, args.subjects, args.max_workers, args.task, args.run)
    extract_parameters_main(args.input_directory, args.output_directory, args.subjects, args.task, args.run)
    first_level_fsfs = generate_design_files_main(
        fsf_template=args.fsf_template,
        output_directory=args.output_directory,
        input_directory=args.input_directory,
        task=args.task,
        custom_block=args.custom_block,
        subjects=args.subjects,
        runs=args.run,
    )

    # Run FEAT or emit FEAT commands for first level.
    run_feat_main(
        first_level_fsfs,
        max_workers=args.max_workers,
        write_commands=args.write_commands,
    )
    if args.higher_level_fsf_template:
        analysis_blocks = args.custom_block if args.custom_block else ["standard"]

        # Pair whichever runs were passed. If more than two, pair the first two.
        run_pair = tuple(args.run[:2]) if len(args.run) >= 2 else (1, 2)

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
            higher_level_fsfs = generate_higher_level_feat_files_main(
                input_directory=first_level_root,
                template_file=args.higher_level_fsf_template,
                design_output_dir=higher_level_design_dir,
                feat_output_dir=higher_level_output_dir,
                run_pair=run_pair,
            )

            if higher_level_fsfs:
                higher_level_fsfs_all.extend(higher_level_fsfs)

        # Run FEAT or emit FEAT commands for higher level.
        run_feat_main(
            higher_level_fsfs_all,
            max_workers=args.max_workers,
            write_commands=args.write_commands,
        )

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
