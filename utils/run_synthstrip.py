#!/usr/bin/env python3

import os
import glob
import subprocess
import concurrent.futures
import logging
import shutil
import sys
import argparse
# Local helpers
from .bids import parse_bids_entities, match_filters
from .command import run_cmd
try:
    import nibabel as nib  # type: ignore
except ImportError:  # pragma: no cover
    # Provide a minimal stub so unit tests can monkeypatch nib.load/save.
    from types import SimpleNamespace

    nib = SimpleNamespace(load=None, save=None, Nifti1Image=None)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Command template for mri_synthstrip
def _synthstrip_cmd(in_path: str, out_path: str) -> list[str]:
    return ["mri_synthstrip", "-i", in_path, "-o", out_path]

def parse_subjects(subjects_input):
    """
    Parse the subjects input.
    If subjects_input is a path to a file, read its contents and split by commas or newlines.
    Otherwise, treat it as a comma-separated list.
    """
    if isinstance(subjects_input, (list, tuple, set)):
        return [str(s).strip() for s in subjects_input if str(s).strip()]
    if os.path.exists(subjects_input) and os.path.isfile(subjects_input):
        with open(subjects_input, 'r') as f:
            content = f.read().strip()
        if ',' in content:
            subjects_list = [s.strip() for s in content.split(',') if s.strip()]
        else:
            subjects_list = [line.strip() for line in content.splitlines() if line.strip()]
    else:
        subjects_list = [s.strip() for s in subjects_input.split(',') if s.strip()]
    return subjects_list

def check_dependencies():
    if not shutil.which("mri_synthstrip"):
        raise RuntimeError("mri_synthstrip is not installed or not found in PATH.")

def process_file(file_path, input_base_dir, output_base_dir, *, log_file=None, dry_run=False, force=False):
    try:
        if not file_path.endswith(".nii.gz"):
            logging.warning(f"Skipping non-NIfTI file: {file_path}")
            return

        # Determine the output directory. Include the additional subdirectory.
        relative_dir = os.path.relpath(os.path.dirname(file_path), input_base_dir)
        output_dir = os.path.join(output_base_dir, "freesurfer_synthstrip_v8.1.0", relative_dir)
        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.basename(file_path)[:-7]  # Remove '.nii.gz'
        output_file = f"{base_name}_synthstrip.nii.gz"
        output_path = os.path.join(output_dir, output_file)

        if os.path.exists(output_path) and not force:
            logging.info(f"Output file already exists, skipping: {output_path}")
            return

        # Load the image to check dimensions.
        img = nib.load(file_path)
        # If the image is 4D with more than one frame, extract the first frame.
        if len(img.shape) == 4 and img.shape[3] > 1:
            logging.info(f"File {file_path} is 4D. Extracting the first frame.")
            first_frame_data = img.dataobj[..., 0]
            # Create a new NIfTI image using the first frame.
            first_frame_img = nib.Nifti1Image(first_frame_data, img.affine, img.header)
            # Save the extracted first frame to a file in the output directory.
            extracted_file = os.path.join(output_dir, f"{base_name}_first_frame.nii.gz")
            nib.save(first_frame_img, extracted_file)
            in_path = extracted_file
        else:
            in_path = file_path

        # Format and run the synthstrip command.
        cmd = _synthstrip_cmd(in_path, output_path)
        run_cmd(cmd, log_file=log_file, dry_run=dry_run, check=True)
        logging.info(f"Completed: {output_path}")

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"mri_synthstrip failed for {file_path}: {e}") from e
    except Exception as e:
        logging.error(f"Unexpected error with file: {file_path}\n{e}")

def gather_nifti_files(input_dir, subjects=None, task_filters=None, run_filters=None):
    """
    Gather NIfTI files from the input directory.
    If a list of subjects is provided, limit the search to those subject directories.
    Otherwise, use the default glob pattern.
    Files that are anatomical (in an "anat" directory and with "T1w" in the filename)
    are always included regardless of task or run filters.
    """
    files = []
    
    # Define a helper that applies the filters.
    def file_matches_filters(f):
        parts = os.path.normpath(f).split(os.sep)
        basename = os.path.basename(f)
        # Always include anatomical T1w images.
        if "anat" in parts and "T1w" in basename:
            return True
        ents = parse_bids_entities(basename)
        return match_filters(ents, task_filters=task_filters, run_filters=run_filters)

    if subjects:
        # subjects is expected to be a list of subject identifiers, e.g., ["sub-001", "sub-002"]
        for sub in subjects:
            subject_dir = os.path.join(input_dir, sub)
            if os.path.isdir(subject_dir):
                pattern = os.path.join(subject_dir, "ses-*", "*", "*.nii.gz")
                sub_files = glob.glob(pattern, recursive=True)
                sub_files = [f for f in sub_files if file_matches_filters(f)]
                files.extend(sub_files)
            else:
                logging.warning(f"Subject directory not found: {subject_dir}")
    else:
        pattern = os.path.join(input_dir, "sub-*", "ses-*", "*", "*.nii.gz")
        all_files = glob.glob(pattern, recursive=True)
        files = [f for f in all_files if file_matches_filters(f)]
    return sorted(files)

def main(
    input_base_dir,
    output_base_dir,
    subjects,
    max_workers=8,
    task_filters=None,
    run_filters=None,
    *,
    log_file=None,
    dry_run=False,
    force=False,
):
    check_dependencies()
    
    # Parse subjects if provided.
    subjects_list = None
    if subjects:
        subjects_list = parse_subjects(subjects)
        logging.info(f"Processing subjects: {subjects_list}")
    
    files_to_process = gather_nifti_files(input_base_dir, subjects_list, task_filters, run_filters)
    logging.info(f"Found {len(files_to_process)} NIfTI files to process.")


    # De-duplicate by intended output path so the same T1w (or any file) is never processed twice
    # even if it appears multiple times in the gathered file list.
    unique = {}
    for fp in files_to_process:
        relative_dir = os.path.relpath(os.path.dirname(fp), input_base_dir)
        output_dir = os.path.join(output_base_dir, "freesurfer_synthstrip_v8.1.0", relative_dir)
        base_name = os.path.basename(fp)[:-7]
        out_fp = os.path.join(output_dir, f"{base_name}_synthstrip.nii.gz")
        unique.setdefault(out_fp, fp)
    files_to_process = list(unique.values())
    logging.info(f"After de-duplication: {len(files_to_process)} NIfTI files to process.")


    if not files_to_process:
        logging.info("No NIfTI files found. Exiting.")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_file,
                fp,
                input_base_dir,
                output_base_dir,
                log_file=log_file,
                dry_run=dry_run,
                force=force,
            ): fp
            for fp in files_to_process
        }
        for future in concurrent.futures.as_completed(futures):
            fp = futures[future]
            try:
                future.result()
            except Exception as e:
                logging.error(f"Unhandled exception for file {fp}: {e}")

    logging.info("Skull-stripping complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run mri_synthstrip on NIfTI files.")
    parser.add_argument("--input_directory", required=True, help="Base directory for input data.")
    parser.add_argument("--output_directory", required=True, help="Base directory for output data.")
    parser.add_argument("--subjects", help=("Optional: Provide a comma-separated list of subjects (e.g., 'sub-001, sub-002') or a path to a text file containing the subjects."))
    parser.add_argument("--max_workers", type=int, default=8, help="Maximum number of parallel workers.")
    parser.add_argument("--task", nargs='+', help=("Optional: Filter files by task substring. For example, passing '--task hand language rest' "
                                                    "will process only files containing 'task-hand', 'task-language', or 'task-rest'."))
    parser.add_argument(
        "--run",
        nargs='+',
        help=(
            "Optional: Filter files by run number. For example, passing '--run 1 2' "
            "will process only files containing 'run-01' or 'run-02'. Use '--run none' to match files with no run label."
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
