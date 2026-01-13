#!/usr/bin/env python3
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate SLURM commands for subject IDs.")
    parser.add_argument("--subject_file", required=True, help="File containing subject IDs (one per line).")
    parser.add_argument("--outdir", default=None, help="Optional output directory for the command file.")
    args = parser.parse_args()

    input_file = args.subject_file

    # Create output file name: use the input file's base name with "-slurm_commands.txt" appended.
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file_name = base_name + "-slurm_commands.txt"

    os.makedirs(args.outdir, exist_ok=True)

    # If an output directory is specified, join it with the output file name.
    if args.outdir:
        output_file = os.path.join(args.outdir, output_file_name)
    else:
        output_file = output_file_name

    # Read subject IDs from the input file (ignoring empty lines)
    try:
        with open(input_file, "r") as f:
            subject_ids = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        exit(1)

    # Template command with a placeholder for subject id
    command_template = (
        "python /autofs/space/nicc_003/users/holly/git/FSL-TaskPipeline/run_pipeline.py --input_directory /autofs/space/nicc_005/users/holly/false_positive "
        "--output_directory /autofs/space/nicc_005/users/holly/false_positive/derivatives "
        "--fsf_template /autofs/space/nicc_003/users/holly/git/FSL-TaskPipeline/design_templates/standard_template.fsf "
        "--task rest --run 1 --subjects {}"
    )

    # Write each command (one per subject id) to the output file
    try:
        with open(output_file, "w") as f_out:
            for subject_id in subject_ids:
                command = command_template.format(subject_id)
                f_out.write(command + "\n")
        print(f"Commands written to {output_file}")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")
        exit(1)

if __name__ == '__main__':
    main()
