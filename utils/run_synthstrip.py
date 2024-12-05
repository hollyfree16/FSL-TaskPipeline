#!/usr/bin/env python3

import os
import glob
import subprocess
import concurrent.futures
import logging
import shutil
import sys
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Command template for mri_synthstrip
command_template = 'mri_synthstrip -i "{in_path}" -o "{out_path}"'

def check_dependencies():
    if not shutil.which("mri_synthstrip"):
        logging.error("Error: mri_synthstrip is not installed or not found in PATH.")
        sys.exit(1)

def process_file(file_path, input_base_dir, output_base_dir):
    try:
        if not file_path.endswith(".nii.gz"):
            logging.warning(f"Skipping non-NIfTI file: {file_path}")
            return

        relative_dir = os.path.relpath(os.path.dirname(file_path), input_base_dir)
        output_dir = os.path.join(output_base_dir, relative_dir)
        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.basename(file_path)[:-7]  # Remove '.nii.gz'
        output_file = f"{base_name}_synthstrip.nii.gz"
        output_path = os.path.join(output_dir, output_file)

        if os.path.exists(output_path):
            logging.info(f"Output file already exists, skipping: {output_path}")
            return

        command = command_template.format(in_path=file_path, out_path=output_path)
        logging.info(f"Running: {command}")

        subprocess.run(command, shell=True, check=True)
        logging.info(f"Completed: {output_path}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Error processing file: {file_path}\n{e}")
    except Exception as e:
        logging.error(f"Unexpected error with file: {file_path}\n{e}")

def gather_nifti_files(input_dir):
    pattern = os.path.join(input_dir, "sub-*", "ses-*", "*", "*.nii.gz")
    return sorted(glob.glob(pattern, recursive=True))

def main(input_base_dir, output_base_dir, max_workers=8):
    check_dependencies()
    files_to_process = gather_nifti_files(input_base_dir)
    logging.info(f"Found {len(files_to_process)} NIfTI files to process.")

    if not files_to_process:
        logging.info("No NIfTI files found. Exiting.")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, fp, input_base_dir, output_base_dir): fp for fp in files_to_process}
        for future in concurrent.futures.as_completed(futures):
            fp = futures[future]
            try:
                future.result()
            except Exception as e:
                logging.error(f"Unhandled exception for file {fp}: {e}")

    logging.info("Skull-stripping complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run mri_synthstrip on NIfTI files.")
    parser.add_argument("--input_base_dir", required=True, help="Base directory for input data.")
    parser.add_argument("--output_base_dir", required=True, help="Base directory for output data.")
    parser.add_argument("--max_workers", type=int, default=8, help="Maximum number of parallel workers.")
    args = parser.parse_args()

    main(args.input_base_dir, args.output_base_dir, args.max_workers)
