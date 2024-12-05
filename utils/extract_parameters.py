#!/usr/bin/env python3

import os
import nibabel as nib
import argparse

def extract_and_write_scan_info(base_dir, output_dir):
    for subject in sorted(os.listdir(base_dir)):
        subject_path = os.path.join(base_dir, subject)
        if not os.path.isdir(subject_path):
            continue

        sessions = os.listdir(subject_path)
        for session in sessions:
            session_path = os.path.join(subject_path, session)
            if not os.path.isdir(session_path):
                continue

            func_path = os.path.join(session_path, 'func')
            if not os.path.exists(func_path):
                continue

            for file in os.listdir(func_path):
                if file.endswith("_synthstrip.nii.gz"):
                    file_path = os.path.join(func_path, file)
                    scan_name = file.replace("_synthstrip.nii.gz", "")
                    config_filename = f"{scan_name}_configuration.md"
                    subject_output_dir = os.path.join(output_dir, "parameters", subject)
                    config_filepath = os.path.join(subject_output_dir, config_filename)

                    if os.path.exists(config_filepath):
                        print(f"Configuration already exists, skipping: {config_filepath}")
                        continue

                    try:
                        nifti_img = nib.load(file_path)
                        header = nifti_img.header

                        tr = header.get_zooms()[3] if len(header.get_zooms()) > 3 else 'N/A'
                        frames = nifti_img.shape[3] if len(nifti_img.shape) > 3 else 'N/A'

                        os.makedirs(subject_output_dir, exist_ok=True)

                        with open(config_filepath, "w") as config_file:
                            config_file.write(f"# {scan_name}_configuration.md\n\n")
                            config_file.write(f"TOTAL_REPETITION_TIME = {tr}\n")
                            config_file.write(f"TOTAL_FRAMES = {frames}\n")
                            config_file.write("DISCARD_FRAMES = 2\n")
                            config_file.write("CRITICAL_Z = 2.3\n")
                            config_file.write("SMOOTHING_KERNEL = 4\n")
                            config_file.write("PROB_THRESHOLD = 0.05\n")
                            config_file.write("Z_THRESHOLD = 3.1\n")
                            config_file.write("Z_MINIMUM = 3.1\n")

                        print(f"Configuration written: {config_filepath}")
                    except Exception as e:
                        print(f"Error processing file {file_path}: {e}")

def main(base_dir, output_dir):
    extract_and_write_scan_info(base_dir, output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract scan information and write configuration files.")
    parser.add_argument("--base_dir", required=True, help="Base directory containing input data.")
    parser.add_argument("--output_dir", required=True, help="Output directory to store configuration files.")
    args = parser.parse_args()

    main(args.base_dir, args.output_dir)
