#!/usr/bin/env python3

import os
import argparse

# nibabel is required for reading NIfTI headers (TR, frame count). We keep this
# import resilient so tests (and lightweight tooling) can monkeypatch `nib.load`
# even in environments where nibabel is not installed.
try:
    import nibabel as nib  # type: ignore
except ModuleNotFoundError:
    class _NibabelStub:
        def load(self, *_args, **_kwargs):
            raise ModuleNotFoundError(
                "nibabel is required to read NIfTI headers for TR and frame count. "
                "Install with: pip install nibabel"
            )

    nib = _NibabelStub()  # type: ignore
from .find_dummy import load_config, get_dummy_scans

def parse_subjects(subjects_input):
    """
    Parse the subjects input.
    If subjects_input is a path to a file, read its contents and split by commas or newlines.
    Otherwise, treat it as a comma-separated list.
    """
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

def extract_and_write_scan_info(base_dir, output_dir, subjects_filter=None, task_filters=None, run_filters=None):
    # Load configuration once at the start
    config = load_config()
    
    # Prepare the output directory for fsl_feat_v6.0.7.4 configurations
    fmri_manager_dir = os.path.join(output_dir, "fsl_feat_v6.0.7.4", "configurations")
    os.makedirs(fmri_manager_dir, exist_ok=True)
    
    # Determine which subjects to process
    if subjects_filter:
        # Only include subjects that exist as directories in base_dir
        subjects = [s for s in subjects_filter if os.path.isdir(os.path.join(base_dir, s))]
    else:
        subjects = sorted(os.listdir(base_dir))
    
    for subject in subjects:
        subject_path = os.path.join(base_dir, subject)
        if not os.path.isdir(subject_path):
            continue

        sessions = sorted(os.listdir(subject_path))
        for session in sessions:
            session_path = os.path.join(subject_path, session)
            print(session_path)
            if not os.path.isdir(session_path):
                continue

            func_path = os.path.join(session_path, 'func')
            if not os.path.exists(func_path):
                continue

            for file in sorted(os.listdir(func_path)):
                # Apply task filtering if provided.
                if task_filters:
                    if not any(f"task-{t}" in file for t in task_filters):
                        continue
                # Apply run filtering if provided.
                if run_filters:
                    if not any(f"run-{int(r):02d}" in file for r in run_filters):
                        continue

                print(func_path, file)
                if file.endswith("_bold.nii.gz"):
                    file_path = os.path.join(func_path, file)
                    scan_name = file.replace("_bold.nii.gz", "")
                    config_filename = f"{scan_name}_configuration.md"
                    
                    # Create subject-specific output directory under the fmri configurations folder
                    subject_output_dir = os.path.join(fmri_manager_dir, subject, session)
                    os.makedirs(subject_output_dir, exist_ok=True)
                    config_filepath = os.path.join(subject_output_dir, config_filename)

                    if os.path.exists(config_filepath):
                        print(f"Configuration already exists, skipping: {config_filepath}")
                        continue

                    try:
                        nifti_img = nib.load(file_path)
                        header = nifti_img.header

                        # Get TR and frame count (if available)
                        tr = header.get_zooms()[3] if len(header.get_zooms()) > 3 else 'N/A'
                        frames = nifti_img.shape[3] if len(nifti_img.shape) > 3 else 'N/A'
                        
                        # Determine the number of dummy scans using the config
                        if isinstance(frames, int):
                            discard_frames = get_dummy_scans(frames, config)
                        else:
                            discard_frames = config.get("default_dummy", 2)

                        # Build the configuration content
                        config_content = (
                            f"# {scan_name}_configuration.md\n\n"
                            f"TOTAL_REPETITION_TIME = {tr}\n"
                            f"TOTAL_FRAMES = {frames}\n"
                            f"DISCARD_FRAMES = {discard_frames}\n"
                            "CRITICAL_Z = 2.3\n"
                            "SMOOTHING_KERNEL = 4\n" ##CHANGED TO 10 06/09/25 FOR DF ANALYSIS 
                            "PROB_THRESHOLD = 0.05\n"
                            "Z_THRESHOLD = 3.1\n"
                            "Z_MINIMUM = 3.1\n"
                        )

                        # Write to the subject-specific "configurations" directory only
                        with open(config_filepath, "w") as config_file:
                            config_file.write(config_content)

                        print(f"Configuration written to: {config_filepath}")
                    except Exception as e:
                        print(f"Error processing file {file_path}: {e}")

def main(base_dir, output_dir, subjects_input=None, task_filters=None, run_filters=None):
    subjects_filter = parse_subjects(subjects_input) if subjects_input else None
    extract_and_write_scan_info(base_dir, output_dir, subjects_filter, task_filters, run_filters)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract scan information and write configuration files.")
    parser.add_argument("--input_directory", required=True, help="Base directory containing input data.")
    parser.add_argument("--output_directory", required=True, help="Output directory to store configuration files.")
    parser.add_argument("--subjects", required=False, help="Comma-separated list or file path containing subjects to process.")
    parser.add_argument("--task", nargs='+', help=("Optional: Filter files by task substring. For example, passing '--task hand language rest' "
                                                    "will process only files containing 'task-hand', 'task-language', or 'task-rest'."))
    parser.add_argument("--run", nargs='+', type=int, help=("Optional: Filter files by run number. For example, passing '--run 1' will process only files containing 'run-01', "
                                                           "or '--run 1 2' will match 'run-01' and 'run-02'."))
    args = parser.parse_args()

    main(args.input_directory, args.output_directory, args.subjects,
         task_filters=args.task, run_filters=args.run)
