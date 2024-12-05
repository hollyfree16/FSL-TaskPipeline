#!/usr/bin/env python3

import os
import glob
import re
from jinja2 import Template
import argparse

def read_parameter_file(param_file_path):
    params = {}
    with open(param_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            params[key.strip()] = value.strip()
    return params

def load_template(template_path):
    with open(template_path, 'r') as f:
        content = f.read()
    return Template(content)

def generate_output_filename(subject_id, task, run, design_type):
    if design_type == "standard":
        return f"{subject_id}_task-{task}_run-{run}_bold_design-standard"
    else:
        return f"{subject_id}_task-{task}_run-{run}_bold_design-{design_type}"

def process_scan(subject_id, session_id, func_file, anat_file, parameter_dir, standard_template, custom_template, 
                 design_files_dir, base_output_dir, custom_config_dir, custom_config_files):
    basename = os.path.basename(func_file)
    match = re.match(r'(sub-\w+)_task-([\w]+)_bold_run-(\d+)_synthstrip\.nii\.gz', basename)
    if not match:
        print(f"Filename {basename} does not match expected pattern. Skipping.")
        return
    sub, task, run = match.groups()

    t1w_path = anat_file
    bold_path = func_file

    param_filename = f"{sub}_task-{task}_bold_run-{run}_configuration.md"
    param_file_path = os.path.join(parameter_dir, param_filename)

    if not os.path.exists(param_file_path):
        print(f"Parameter file {param_file_path} not found. Skipping.")
        return

    params = read_parameter_file(param_file_path)

    total_repetition_time = params.get("TOTAL_REPETITION_TIME")
    total_frames = params.get("TOTAL_FRAMES")
    discard_frames = params.get("DISCARD_FRAMES")
    critical_z = params.get("CRITICAL_Z")
    smoothing_kernel = params.get("SMOOTHING_KERNEL")
    prob_threshold = params.get("PROB_THRESHOLD")
    z_threshold = params.get("Z_THRESHOLD")
    z_minimum = params.get("Z_MINIMUM")

    confound_pattern = f"{sub}_task-{task}_bold_run-{run}_confounds.txt"
    confound_file = os.path.join(os.path.dirname(func_file), confound_pattern)
    confound_exists = os.path.exists(confound_file)

    output_dir_name = generate_output_filename(sub, task, run, "standard")
    output_directory = os.path.join(base_output_dir, sub, output_dir_name)
    standard_design_filename = f"{output_dir_name}.fsf"
    standard_design_path = os.path.join(design_files_dir, standard_design_filename)

    if os.path.exists(standard_design_path):
        print(f"Design file already exists, skipping: {standard_design_path}")
    else:
        replacements_standard = {
            "OUTPUT_DIRECTORY": output_directory,
            "TOTAL_REPETITION_TIME": total_repetition_time,
            "TOTAL_FRAMES": total_frames,
            "DISCARD_FRAMES": discard_frames,
            "CRITICAL_Z": critical_z,
            "SMOOTHING_KERNEL": smoothing_kernel,
            "PROB_THRESHOLD": prob_threshold,
            "Z_THRESHOLD": z_threshold,
            "Z_MINIMUM": z_minimum,
            "FULL_STRUCTURAL_PATH": t1w_path,
            "FULL_FUNCTIONAL_PATH": bold_path,
            "CUSTOM_DESIGN_FILE": "",
            "fmri_confoundevs": "1" if confound_exists else "0",
            "FULL_CONFOUND_PATH": confound_file if confound_exists else "",
            "FUNCTIONAL_TASK_NAME": task
        }

        standard_design_content = standard_template.render(**replacements_standard)

        os.makedirs(design_files_dir, exist_ok=True)
        with open(standard_design_path, 'w') as f:
            f.write(standard_design_content)
        print(f"Generated standard design file: {standard_design_path}")

    if task.lower() != "rest":
        for custom_config in custom_config_files:
            custom_config_path = os.path.join(custom_config_dir, custom_config)
            if not os.path.exists(custom_config_path):
                print(f"Custom config file {custom_config_path} not found. Skipping.")
                continue

            custom_type = custom_config.replace('_config.txt', '')
            custom_output_dir_name = generate_output_filename(sub, task, run, custom_type)
            custom_output_directory = os.path.join(base_output_dir, sub, custom_output_dir_name)
            custom_design_filename = f"{custom_output_dir_name}.fsf"
            custom_design_path = os.path.join(design_files_dir, custom_design_filename)

            if os.path.exists(custom_design_path):
                print(f"Custom design file already exists, skipping: {custom_design_path}")
                continue

            replacements_custom = {
                "OUTPUT_DIRECTORY": custom_output_directory,
                "TOTAL_REPETITION_TIME": total_repetition_time,
                "TOTAL_FRAMES": total_frames,
                "DISCARD_FRAMES": discard_frames,
                "CRITICAL_Z": critical_z,
                "SMOOTHING_KERNEL": smoothing_kernel,
                "PROB_THRESHOLD": prob_threshold,
                "Z_THRESHOLD": z_threshold,
                "Z_MINIMUM": z_minimum,
                "FULL_STRUCTURAL_PATH": t1w_path,
                "FULL_FUNCTIONAL_PATH": bold_path,
                "CUSTOM_DESIGN_FILE": custom_config_path,
                "fmri_confoundevs": "1" if confound_exists else "0",
                "FULL_CONFOUND_PATH": confound_file if confound_exists else "",
                "FUNCTIONAL_TASK_NAME": task
            }

            custom_design_content = custom_template.render(**replacements_custom)

            os.makedirs(design_files_dir, exist_ok=True)
            with open(custom_design_path, 'w') as f:
                f.write(custom_design_content)
            print(f"Generated custom design file: {custom_design_path}")

def main(preprocessing_dir, design_files_dir, parameter_files_root, custom_config_dir, 
         standard_template_path, custom_template_path, base_output_dir):
    standard_template = load_template(standard_template_path)
    custom_template = load_template(custom_template_path)

    subject_dirs = glob.glob(os.path.join(preprocessing_dir, "sub-*"))
    custom_config_files = ["alternating_config.txt", "inverted_config.txt", "split_config.txt", "staggered_config.txt"]

    for subject_dir in subject_dirs:
        subject_id = os.path.basename(subject_dir)
        parameter_dir = os.path.join(parameter_files_root, subject_id)

        if not os.path.exists(parameter_dir):
            print(f"Parameter directory {parameter_dir} does not exist. Skipping subject {subject_id}.")
            continue

        session_dirs = glob.glob(os.path.join(subject_dir, "ses-*"))

        for session_dir in session_dirs:
            anat_dir = os.path.join(session_dir, "anat")
            func_dir = os.path.join(session_dir, "func")

            anat_pattern = f"{subject_id}_T1w_synthstrip.nii.gz"
            anat_files = glob.glob(os.path.join(anat_dir, anat_pattern))
            if not anat_files:
                print(f"No anatomical file found in {anat_dir} for subject {subject_id}. Skipping session.")
                continue
            anat_file = anat_files[0]

            func_pattern = f"{subject_id}_task-*_bold_run-*_synthstrip.nii.gz"
            func_files = glob.glob(os.path.join(func_dir, func_pattern))
            if not func_files:
                print(f"No functional files found in {func_dir} for subject {subject_id}. Skipping session.")
                continue

            for func_file in func_files:
                process_scan(subject_id, os.path.basename(session_dir), func_file, anat_file, 
                             parameter_dir, standard_template, custom_template, 
                             design_files_dir, base_output_dir, custom_config_dir, custom_config_files)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate FSL design files for fMRI analysis.")
    parser.add_argument("--preprocessing_dir", required=True, help="Path to preprocessing directory.")
    parser.add_argument("--design_files_dir", required=True, help="Path to design files output directory.")
    parser.add_argument("--parameter_files_root", required=True, help="Path to parameter files root directory.")
    parser.add_argument("--custom_config_dir", required=True, help="Path to custom configuration directory.")
    parser.add_argument("--standard_template_path", required=True, help="Path to standard design template.")
    parser.add_argument("--custom_template_path", required=True, help="Path to custom design template.")
    parser.add_argument("--base_output_dir", required=True, help="Base output directory for FEAT analyses.")
    args = parser.parse_args()

    main(args.preprocessing_dir, args.design_files_dir, args.parameter_files_root, 
         args.custom_config_dir, args.standard_template_path, args.custom_template_path, 
         args.base_output_dir)
