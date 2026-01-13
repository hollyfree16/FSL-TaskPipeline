import argparse
import os
import glob
from jinja2 import Environment, FileSystemLoader
import subprocess

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
                # Look for session directories within the subject directory
                session_dirs = glob.glob(os.path.join(subject_path, "ses-*"))
                if session_dirs:
                    subject_dirs.extend(session_dirs)  # Add session directories
                else:
                    print(f"Warning: No session directories found in {subject_path}")
            else:
                print(f"Warning: Subject directory not found: {subject_path}")

    else:
        # Auto-detect all subjects and sessions
        subject_dirs = sorted(glob.glob(os.path.join(input_base_dir, "sub-*", "ses-*")))

    return subject_dirs

def extract_subject_session_from_path(path):
    """Extracts the subject ID and session ID from a given path.
    
    If the path is a directory (subject/session), then the subject is assumed to be the parent
    directory and the session is the basename. Otherwise, for a file path, the function 
    examines the parent directories.
    """
    if os.path.isdir(path):
        # For directory paths like .../sub-R2c001/ses-001
        subject_id = os.path.basename(os.path.dirname(path))
        session_id = os.path.basename(path)
    else:
        # For file paths, use the parent directory
        parts = os.path.dirname(path).split(os.sep)
        subject_id = None
        session_id = None
        for part in parts:
            if part.startswith("sub-"):
                subject_id = part
            elif part.startswith("ses-"):
                session_id = part
    return subject_id, session_id

def generate_fsf(config, fsf_template, output_directory, input_directory, task, custom_block, run_number, subject, session, space):
    """Generates an FSF file based on the given parameters, looping over custom blocks."""
    subject_design_output = os.path.join(
        output_directory,
        "fsl_feat_v6.0.7.4",
        "subject_designs",
        f"space-{space}",
    )
    os.makedirs(subject_design_output, exist_ok=True)
    
    # Extract subject and session from the config file path
    subject_id, session_id = extract_subject_session_from_path(config)
    block_dir = os.path.dirname(fsf_template)

    if not subject_id or not session_id:
        print(f"Error: Could not extract subject and session from path: {config}")
        return

    # Parse configuration file parameters
    config_params = parse_config_file(config)

    # Construct common paths
    structural_path = f"{output_directory}/freesurfer_synthstrip_v8.1.0/{subject_id}/{session_id}/anat/{subject_id}_{session_id}_T1w_synthstrip.nii.gz"
    functional_path = f"{input_directory}/{subject_id}/{session_id}/func/{subject_id}_{session_id}_task-{task}_run-{run_number:02d}_bold.nii.gz"
    func_reg_image = f"{output_directory}/freesurfer_synthstrip_v8.1.0/{subject_id}/{session_id}/func/{subject_id}_{session_id}_task-{task}_run-{run_number:02d}_bold_first_frame.nii.gz"
    
    # Check for confound file
    confound_path = f"{output_directory}/fsl_motion-outliers_v6.0.7.4/{subject_id}/{session_id}/func/{subject_id}_{session_id}_task-{task}_run-{run_number:02d}_confounds.txt"
    full_confound_path = check_file_exists(confound_path)
    fmri_confoundevs = "1" if full_confound_path else "0"

    # If no custom block is provided, default to "standard"
    if not custom_block:
        custom_block = ["standard"]

    # Loop over each custom block provided
    for block in custom_block:
        # Use the custom block name directly as the analysis subdirectory
        analysis = block  
        feat_directory = os.path.join(
            output_directory,
            "fsl_feat_v6.0.7.4",
            analysis,
            f"space-{space}",
            subject,
            session,
            f"{subject}_{session}_task-{task}_run-{run_number:02d}"
        )

        # Build the custom design file path (assumes a .txt file in the same directory as the fsf_template)
        custom_design_file = os.path.join(block_dir, f"{block}.txt")
        if not os.path.exists(custom_design_file):
            print(f"Warning: Custom design file not found: {custom_design_file}")
            custom_design_file_str = ""
        else:
            custom_design_file_str = custom_design_file

        # Load Jinja2 template
        env = Environment(loader=FileSystemLoader(os.path.dirname(fsf_template)))
        template = env.get_template(os.path.basename(fsf_template))

        # Render template using the custom design file for this block
        rendered_fsf = template.render(
            OUTPUT_DIRECTORY=feat_directory,
            FULL_STRUCTURAL_PATH=structural_path,
            FULL_FUNCTIONAL_PATH=functional_path,
            FUNC_REG_IMAGE=func_reg_image,
            CUSTOM_DESIGN_FILE=custom_design_file_str,
            fmri_confoundevs=fmri_confoundevs,
            FULL_CONFOUND_PATH=full_confound_path,
            FUNCTIONAL_TASK_NAME=task,
            **config_params  # e.g., TOTAL_REPETITION_TIME, DISCARD_FRAMES, etc.
        )

        # Generate a unique output FSF filename; append the block name if not "standard"
        output_fsf_filename = f"{subject_id}_{session_id}_task-{task}_run-{run_number:02d}"
        if block != "standard":
            output_fsf_filename += f"_{block}"
        output_fsf_filename += ".fsf"
        output_fsf_path = os.path.join(subject_design_output, output_fsf_filename)

        with open(output_fsf_path, 'w') as fsf_file:
            fsf_file.write(rendered_fsf)

        print(f"FSF file generated: {output_fsf_path}")

        # Run FEAT on the generated FSF file
        try:
            subprocess.run(["feat", output_fsf_path], check=True)
            print(f"FEAT analysis started for {output_fsf_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error running FEAT for {output_fsf_path}: {e}")


def main(fsf_template, output_directory, input_directory, task, custom_block, subjects, runs, space="native"):
    """Main function to generate FSF files for multiple subjects, sessions, and runs."""

    # Get subject session directories
    subject_dirs = parse_subjects(subjects, input_directory)
    
    # Iterate over subject/session directories
    for subject_dir in subject_dirs:
        subject_id, session_id = extract_subject_session_from_path(subject_dir)

        if subject_id and session_id:
            for run_number in runs:
                config_file = os.path.join(
                    output_directory,
                    f"fsl_feat_v6.0.7.4/configurations/{subject_id}/{session_id}",
                    f"{subject_id}_{session_id}_task-{task}_run-{run_number:02d}_configuration.md"
                )

                if os.path.exists(config_file):
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
                        space=space,
                    )
                else:
                    print(f"Warning: Configuration file not found for {subject_id} {session_id} run-{run_number} at {config_file}")
        else:
            print(f"Skipping invalid directory: {subject_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate FSF files from configuration.")
    parser.add_argument("--fsf_template", required=True, help="Path to the .fsf template file.")
    parser.add_argument("--output_directory", required=True, help="Output directory for generated files.")
    parser.add_argument("--input_directory", required=True, help="Input directory containing functional files.")
    parser.add_argument("--task", required=True, help="Task name (e.g., hand).")
    parser.add_argument("--custom_block", nargs='*', default=[], help="Custom block inputs (optional).")
    parser.add_argument("--subjects", required=False, help="Path to a subjects file or a comma-separated list of subjects.")
    parser.add_argument("--run", nargs='+', type=int, required=True, help="Run numbers to process (e.g., --run 1 2).")
    parser.add_argument("--space", default="native", help="Output space label for FEAT directories (default: native).")

    args = parser.parse_args()

    main(
        fsf_template=args.fsf_template,
        output_directory=args.output_directory,
        input_directory=args.input_directory,
        task=args.task,
        custom_block=args.custom_block,
        subjects=args.subjects,
        runs=args.run,
        space=args.space,
    )
