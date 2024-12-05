#!/usr/bin/env python3

import argparse
import sys
import os
from utils.run_motion_outliers import main as run_motion_outliers_main
from utils.run_synthstrip import main as run_synthstrip_main
from utils.extract_parameters import main as extract_parameters_main
from utils.generate_design_files import main as generate_design_files_main

def main():
    parser = argparse.ArgumentParser(description="Wrapper script to run all FSL Task Pipeline steps.")

    # Arguments for run_motion_outliers
    parser.add_argument("--motion_input_base_dir", required=True, help="Input directory for motion outliers.")
    parser.add_argument("--motion_output_base_dir", required=True, help="Output directory for motion outliers.")
    parser.add_argument("--motion_max_workers", type=int, default=10, help="Max workers for motion outliers.")

    # Arguments for run_synthstrip
    parser.add_argument("--synthstrip_input_base_dir", required=True, help="Input directory for skull stripping.")
    parser.add_argument("--synthstrip_output_base_dir", required=True, help="Output directory for skull stripping.")
    parser.add_argument("--synthstrip_max_workers", type=int, default=8, help="Max workers for skull stripping.")

    # Arguments for extract_parameters
    parser.add_argument("--extract_base_dir", required=True, help="Base directory for extracting scan info.")
    parser.add_argument("--extract_output_dir", required=True, help="Output directory for scan info.")

    # Arguments for generate_design_files
    parser.add_argument("--preprocessing_dir", required=True, help="Path to preprocessing directory.")
    parser.add_argument("--design_files_dir", required=True, help="Path to design files output directory.")
    parser.add_argument("--parameter_files_root", required=True, help="Path to parameter files root directory.")
    parser.add_argument("--custom_config_dir", required=True, help="Path to custom configuration directory.")
    parser.add_argument("--standard_template_path", required=True, help="Path to standard design template.")
    parser.add_argument("--custom_template_path", required=True, help="Path to custom design template.")
    parser.add_argument("--base_output_dir", required=True, help="Base output directory for FEAT analyses.")

    args = parser.parse_args()

    # Run run_motion_outliers
    run_motion_outliers_main(args.motion_input_base_dir, args.motion_output_base_dir, args.motion_max_workers)

    # Run run_synthstrip
    run_synthstrip_main(args.synthstrip_input_base_dir, args.synthstrip_output_base_dir, args.synthstrip_max_workers)

    # Run extract_parameters
    extract_parameters_main(args.extract_base_dir, args.extract_output_dir)

    # Run generate_design_files
    generate_design_files_main(
        args.preprocessing_dir,
        args.design_files_dir,
        args.parameter_files_root,
        args.custom_config_dir,
        args.standard_template_path,
        args.custom_template_path,
        args.base_output_dir
    )

    print("All pipeline steps completed successfully!")

if __name__ == "__main__":
    main()
