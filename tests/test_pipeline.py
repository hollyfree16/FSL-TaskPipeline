import pytest
import sys
from unittest.mock import patch, MagicMock
import run_pipeline
import os

# Test the main function of the wrapper
def test_run_pipeline_main(tmp_path):
    # Mock arguments for the pipeline script
    mock_args = [
        "--motion_input_base_dir", str(tmp_path / "motion_input"),
        "--motion_output_base_dir", str(tmp_path / "motion_output"),
        "--motion_max_workers", "5",
        "--synthstrip_input_base_dir", str(tmp_path / "synthstrip_input"),
        "--synthstrip_output_base_dir", str(tmp_path / "synthstrip_output"),
        "--synthstrip_max_workers", "4",
        "--extract_base_dir", str(tmp_path / "extract_base"),
        "--extract_output_dir", str(tmp_path / "extract_output"),
        "--preprocessing_dir", str(tmp_path / "preprocessing"),
        "--design_files_dir", str(tmp_path / "design_files"),
        "--parameter_files_root", str(tmp_path / "parameters"),
        "--custom_config_dir", str(tmp_path / "configs"),
        "--standard_template_path", "configuration_templates/standard_design_template.fsf",
        "--custom_template_path", "configuration_templates/custom_design_template.fsf",
        "--base_output_dir", str(tmp_path / "base_output")
    ]

    with patch.object(sys, "argv", ["run_pipeline.py"] + mock_args):
        # Mock the main functions of each utility script
        with patch("run_pipeline.run_motion_outliers_main", autospec=True) as mock_motion_outliers, \
             patch("run_pipeline.run_synthstrip_main", autospec=True) as mock_synthstrip, \
             patch("run_pipeline.extract_parameters_main", autospec=True) as mock_extract_parameters, \
             patch("run_pipeline.generate_design_files_main", autospec=True) as mock_generate_design_files, \
             patch("os.listdir", return_value=["sub-001", "sub-002"]) as mock_listdir, \
             patch("os.path.isdir", return_value=True) as mock_isdir, \
             patch("os.makedirs") as mock_makedirs:

            # Call the main function
            run_pipeline.main()

            # Debugging: Print calls to mock_motion_outliers
            print("Mock motion_outliers calls:", mock_motion_outliers.mock_calls)

            # Verify each utility function is called with the correct arguments
            mock_motion_outliers.assert_called_once_with(
                str(tmp_path / "motion_input"), str(tmp_path / "motion_output"), 5
            )
            mock_synthstrip.assert_called_once_with(
                str(tmp_path / "synthstrip_input"), str(tmp_path / "synthstrip_output"), 4
            )
            mock_extract_parameters.assert_called_once_with(
                str(tmp_path / "extract_base"), str(tmp_path / "extract_output")
            )
            mock_generate_design_files.assert_called_once_with(
                str(tmp_path / "preprocessing"),
                str(tmp_path / "design_files"),
                str(tmp_path / "parameters"),
                str(tmp_path / "configs"),
                "configuration_templates/standard_design_template.fsf",
                "configuration_templates/custom_design_template.fsf",
                str(tmp_path / "base_output")
            )

# Test for missing arguments
def test_run_pipeline_missing_args():
    with patch.object(sys, "argv", ["run_pipeline.py"]):  # No arguments provided
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            run_pipeline.main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code != 0  # Expect non-zero exit code for missing args
