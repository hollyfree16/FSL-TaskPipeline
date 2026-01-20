import argparse
import os
import glob
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader


def parse_config_file(config_path):
    """Parses the configuration file and extracts relevant parameters."""
    params = {}
    with open(config_path, 'r') as file:
        for line in file:
            if '=' in line:
                key, value = line.strip().split('=')
                params[key.strip()] = value.strip()
    return params


def check_file_exists(path_pattern):
    """Checks if a file matching the given pattern exists."""
    files = glob.glob(path_pattern)
    return files[0] if files else ""


def parse_subjects(subjects, input_base_dir):
    """Parses subjects from a file or comma-separated list, or finds all 'sub-*/ses-*' directories."""
    subject_dirs = []

    if subjects:
        if os.path.exists(subjects) and os.path.isfile(subjects):
            with open(subjects, 'r') as f:
                content = f.read().strip()
            if ',' in content:
                subjects_list = [s.strip() for s in content.split(',') if s.strip()]
            else:
                subjects_list = [line.strip() for line in content.splitlines() if line.strip()]
        else:
            subjects_list = [s.strip() for s in subjects.split(',') if s.strip()]

        # Find session directories inside each subject directory
        for sub in subjects_list:
            subject_path = os.path.join(input_base_dir, sub)
            if os.path.exists(subject_path) and os.path.isdir(subject_path):
                session_dirs = glob.glob(os.path.join(subject_path, "ses-*"))
                if session_dirs:
                    subject_dirs.extend(session_dirs)
                else:
                    print(f"Warning: No session directories found in {subject_path}")
            else:
                print(f"Warning: Subject directory not found: {subject_path}")

    else:
        subject_dirs = sorted(glob.glob(os.path.join(input_base_dir, "sub-*", "ses-*")))

    return subject_dirs


def extract_subject_session_from_path(path):
    """Extracts the subject ID and session ID from a given path."""
    if os.path.isdir(path):
        subject_id = os.path.basename(os.path.dirname(path))
        session_id = os.path.basename(path)
    else:
        parts = os.path.dirname(path).split(os.sep)
        subject_id = None
        session_id = None
        for part in parts:
            if part.startswith("sub-"):
                subject_id = part
            elif part.startswith("ses-"):
                session_id = part
    return subject_id, session_id


def generate_fsf(
    *,
    config: str,
    fsf_template: str,
    output_directory: str,
    input_directory: str,
    task: str,
    custom_block: List[str],
    run_number: int,
    subject: str,
    session: str,
) -> List[str]:
    """Generate one or more FSF files (standard + optional custom blocks).

    Returns a list of paths to generated FSF files.
    """
    generated: List[str] = []

    subject_design_output = os.path.join(
        output_directory,
        "fsl_feat_v6.0.7.4",
        "subject_designs",
    )
    os.makedirs(subject_design_output, exist_ok=True)

    subject_id, session_id = extract_subject_session_from_path(config)
    block_dir = os.path.dirname(fsf_template)

    if not subject_id or not session_id:
        print(f"Error: Could not extract subject and session from path: {config}")
        return generated

    config_params = parse_config_file(config)

    structural_path = (
        f"{output_directory}/freesurfer_synthstrip_v8.1.0/{subject_id}/{session_id}/anat/"
        f"{subject_id}_{session_id}_T1w_synthstrip.nii.gz"
    )
    functional_path = (
        f"{input_directory}/{subject_id}/{session_id}/func/"
        f"{subject_id}_{session_id}_task-{task}_run-{run_number:02d}_bold.nii.gz"
    )
    func_reg_image = (
        f"{output_directory}/freesurfer_synthstrip_v8.1.0/{subject_id}/{session_id}/func/"
        f"{subject_id}_{session_id}_task-{task}_run-{run_number:02d}_bold_first_frame.nii.gz"
    )

    confound_path = (
        f"{output_directory}/fsl_motion-outliers_v6.0.7.4/{subject_id}/{session_id}/func/"
        f"{subject_id}_{session_id}_task-{task}_run-{run_number:02d}_confounds.txt"
    )
    full_confound_path = check_file_exists(confound_path)
    fmri_confoundevs = "1" if full_confound_path else "0"

    if not custom_block:
        custom_block = ["standard"]

    for block in custom_block:
        analysis = block
        feat_directory = os.path.join(
            output_directory,
            "fsl_feat_v6.0.7.4",
            analysis,
            subject,
            session,
            f"{subject}_{session}_task-{task}_run-{run_number:02d}",
        )

        custom_design_file = os.path.join(block_dir, f"{block}.txt")
        if not os.path.exists(custom_design_file):
            print(f"Warning: Custom design file not found: {custom_design_file}")
            custom_design_file_str = ""
        else:
            custom_design_file_str = custom_design_file

        env = Environment(loader=FileSystemLoader(os.path.dirname(fsf_template)))
        template = env.get_template(os.path.basename(fsf_template))

        rendered_fsf = template.render(
            OUTPUT_DIRECTORY=feat_directory,
            FULL_STRUCTURAL_PATH=structural_path,
            FULL_FUNCTIONAL_PATH=functional_path,
            FUNC_REG_IMAGE=func_reg_image,
            CUSTOM_DESIGN_FILE=custom_design_file_str,
            fmri_confoundevs=fmri_confoundevs,
            FULL_CONFOUND_PATH=full_confound_path,
            FUNCTIONAL_TASK_NAME=task,
            **config_params,
        )

        output_fsf_filename = f"{subject_id}_{session_id}_task-{task}_run-{run_number:02d}"
        if block != "standard":
            output_fsf_filename += f"_{block}"
        output_fsf_filename += ".fsf"
        output_fsf_path = os.path.join(subject_design_output, output_fsf_filename)

        with open(output_fsf_path, 'w') as fsf_file:
            fsf_file.write(rendered_fsf)

        print(f"FSF file generated: {output_fsf_path}")
        generated.append(output_fsf_path)

    return generated


def main(
    *,
    fsf_template: str,
    output_directory: str,
    input_directory: str,
    task: str,
    custom_block: List[str],
    subjects: Optional[str],
    runs: List[int],
) -> List[str]:
    """Generate FSF files for multiple subjects, sessions, and runs.

    Returns a flat list of generated FSF paths.
    """
    all_generated: List[str] = []

    subject_dirs = parse_subjects(subjects, input_directory)

    for subject_dir in subject_dirs:
        subject_id, session_id = extract_subject_session_from_path(subject_dir)

        if subject_id and session_id:
            for run_number in runs:
                config_file = os.path.join(
                    output_directory,
                    f"fsl_feat_v6.0.7.4/configurations/{subject_id}/{session_id}",
                    f"{subject_id}_{session_id}_task-{task}_run-{run_number:02d}_configuration.md",
                )

                if os.path.exists(config_file):
                    all_generated.extend(
                        generate_fsf(
                            config=config_file,
                            fsf_template=fsf_template,
                            output_directory=output_directory,
                            input_directory=input_directory,
                            task=task,
                            custom_block=custom_block,
                            run_number=run_number,
                            subject=subject_id,
                            session=session_id,
                        )
                    )
                else:
                    print(
                        f"Warning: Configuration file not found for {subject_id} {session_id} "
                        f"run-{run_number} at {config_file}"
                    )
        else:
            print(f"Skipping invalid directory: {subject_dir}")

    return all_generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate FSF files from configuration.")
    parser.add_argument("--fsf_template", required=True, help="Path to the .fsf template file.")
    parser.add_argument("--output_directory", required=True, help="Output directory for generated files.")
    parser.add_argument("--input_directory", required=True, help="Input directory containing functional files.")
    parser.add_argument("--task", required=True, help="Task name (e.g., hand).")
    parser.add_argument("--custom_block", nargs='*', default=[], help="Custom block inputs (optional).")
    parser.add_argument(
        "--subjects",
        required=False,
        help="Path to a subjects file or a comma-separated list of subjects.",
    )
    parser.add_argument("--run", nargs='+', type=int, required=True, help="Run numbers to process (e.g., --run 1 2).")

    args = parser.parse_args()

    main(
        fsf_template=args.fsf_template,
        output_directory=args.output_directory,
        input_directory=args.input_directory,
        task=args.task,
        custom_block=args.custom_block,
        subjects=args.subjects,
        runs=args.run,
    )
