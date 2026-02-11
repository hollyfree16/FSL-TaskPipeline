#!/usr/bin/env python3

import os
import glob
import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import nibabel as nib  # type: ignore
except ImportError:  # pragma: no cover
    nib = None
from functools import partial
from .find_dummy import load_config, get_dummy_scans
from .bids import parse_bids_entities, match_filters
from .command import run_cmd
from .subjects import parse_subjects_arg

def process_file(input_path, output_path, config, *, log_file=None, dry_run=False, force=False):
    """
    Process a single NIfTI file: determine the number of frames,
    update the fsl_motion_outliers command with the appropriate --dummy value,
    and run the command.
    """
    if os.path.exists(output_path) and not force:
        print(f"Output file already exists, skipping: {output_path}")
        return

    # Determine number of frames in the bold sequence
    try:
        if nib is None:
            raise ImportError("nibabel not installed")

        img = nib.load(input_path)
        if len(img.shape) < 4:
            print(f"File {input_path} does not have 4 dimensions, cannot determine number of frames. Using default dummy scans.")
            num_frames = None
        else:
            num_frames = img.shape[3]
    except Exception as e:
        print(f"Error loading {input_path} to determine number of frames: {e}. Using default dummy scans.")
        num_frames = None

    # Determine dummy scans using config settings
    if num_frames is not None:
        dummy_scans = get_dummy_scans(num_frames, config)
    else:
        dummy_scans = config.get("default_dummy", 2)

    # Update command template with computed dummy_scans value
    cmd = [
        "fsl_motion_outliers",
        "-i",
        input_path,
        "-o",
        output_path,
        f"--dummy={dummy_scans}",
        "-v",
        "--dvars",
    ]
    try:
        run_cmd(cmd, log_file=log_file, dry_run=dry_run, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"fsl_motion_outliers failed for {input_path}: {e}") from e

def main(
    input_base_dir,
    output_base_dir,
    subjects,
    max_workers=10,
    task_filters=None,
    run_filters=None,
    *,
    log_file=None,
    dry_run=False,
    force=False,
):
    tasks = []
    
    # Load configuration settings for motion outlier detection.
    config = load_config()
    
    # Determine which subject directories to process:
    subjects_list = parse_subjects_arg(subjects)
    if subjects_list:
        subject_dirs = [os.path.join(input_base_dir, sub) for sub in subjects_list]
    else:
        subject_dirs = sorted(glob.glob(os.path.join(input_base_dir, "sub-*")))
    
    # Loop through each subject directory.
    for sub_dir in subject_dirs:
        if not os.path.isdir(sub_dir):
            print(f"Warning: subject directory {sub_dir} does not exist. Skipping.")
            continue
        
        # Walk the subject directory to find functional data.
        for root, dirs, files in os.walk(sub_dir):
            if "func" in root:
                for file in files:
                    if file.endswith(".nii.gz") and "bold" in file:
                        ents = parse_bids_entities(file)
                        if not match_filters(ents, task_filters=task_filters, run_filters=run_filters):
                            continue
                        input_path = os.path.join(root, file)
                        # Compute the relative path from the input_base_dir.
                        relative_path = os.path.relpath(root, input_base_dir)
                        # Include the additional directory for outputs.
                        output_dir = os.path.join(output_base_dir, "fsl_motion-outliers_v6.0.7.4", relative_path)
                        # Create the directory if it doesn't exist.
                        os.makedirs(output_dir, exist_ok=True)
                        
                        base_name = os.path.splitext(os.path.splitext(file)[0])[0]
                        output_file = f"{base_name}_confounds.txt"
                        output_path = os.path.join(output_dir, output_file)
                        
                        tasks.append((input_path, output_path))
    
    # Process files in parallel, passing the configuration to each worker.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        func = partial(process_file, config=config, log_file=log_file, dry_run=dry_run, force=force)
        futures = [executor.submit(func, *task) for task in tasks]
        for future in as_completed(futures):
            future.result()
    
    print("Motion outlier detection complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run FSL motion outlier detection on fMRI data."
    )
    parser.add_argument("--input_directory", required=True, help="Base directory for input data.")
    parser.add_argument("--output_directory", required=True, help="Base directory for output data.")
    parser.add_argument("--subjects", help=("Optional: Provide a comma-separated list of subjects (e.g., 'sub-001, sub-002') or a path to a text file containing the subjects."))
    parser.add_argument("--max_workers", type=int, default=10, help="Maximum number of parallel workers.")
    parser.add_argument("--task", nargs='+', help=("Optional: Filter files by task substring. For example, passing '--task hand language rest' "
                                                    "will process only files containing 'task-hand', 'task-language', or 'task-rest'."))
    parser.add_argument(
        "--run",
        nargs='+',
        help=(
            "Optional: Filter files by run number. For example, passing '--run 1' will process only files containing 'run-01', "
            "or '--run 1 2 3' will match 'run-01', 'run-02', and 'run-03'. Use '--run none' to match files with no run label."
        ),
    )
    args = parser.parse_args()

    run_filters = None
    if args.run:
        normalized = [str(r).strip().lower() for r in args.run]
        if "none" in normalized:
            if len(normalized) != 1:
                raise SystemExit("--run none cannot be combined with numeric runs")
            run_filters = [None]
        else:
            run_filters = [int(r) for r in normalized]
    
    main(
        args.input_directory,
        args.output_directory,
        args.subjects,
        args.max_workers,
        task_filters=args.task,
        run_filters=run_filters,
    )
