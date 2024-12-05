#!/usr/bin/env python3

import os
import glob
import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor

# Command template for fsl_motion_outliers
command_template = (
    "fsl_motion_outliers -i {input} -o {output} --dummy=2 -v --dvars"
)

# Function to execute a single command
def process_file(input_path, output_path):
    if os.path.exists(output_path):
        print(f"Output file already exists, skipping: {output_path}")
        return
    command = command_template.format(input=input_path, output=output_path)
    print(f"Running: {command}")
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error processing file: {input_path}\n{e}")

def main(input_base_dir, output_base_dir, max_workers=10):
    tasks = []

    # Traverse input directory and process only functional data
    for sub_dir in sorted(glob.glob(os.path.join(input_base_dir, "sub-*"))):
        for root, dirs, files in os.walk(sub_dir):
            if "func" in root:
                for file in files:
                    if file.endswith(".nii.gz") and "bold" in file:
                        input_path = os.path.join(root, file)
                        relative_path = os.path.relpath(root, input_base_dir)
                        output_dir = os.path.join(output_base_dir, relative_path)
                        os.makedirs(output_dir, exist_ok=True)

                        base_name = os.path.splitext(os.path.splitext(file)[0])[0]
                        output_file = f"{base_name}_confounds.txt"
                        output_path = os.path.join(output_dir, output_file)

                        tasks.append((input_path, output_path))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda task: process_file(*task), tasks)

    print("Motion outlier detection complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FSL motion outlier detection on fMRI data.")
    parser.add_argument("--input_base_dir", required=True, help="Base directory for input data.")
    parser.add_argument("--output_base_dir", required=True, help="Base directory for output data.")
    parser.add_argument("--max_workers", type=int, default=10, help="Maximum number of parallel workers.")
    args = parser.parse_args()

    main(args.input_base_dir, args.output_base_dir, args.max_workers)
