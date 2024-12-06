import os
import pytest
from unittest.mock import patch, MagicMock
from jinja2 import Template
from utils import generate_design_files  # Adjust for your project directory

# Fixture to create a mock directory structure
@pytest.fixture
def mock_file_structure(tmp_path):
    preprocessing_dir = tmp_path / "preprocessing"
    design_files_dir = tmp_path / "design_files"
    parameter_files_root = tmp_path / "parameters"
    custom_config_dir = tmp_path / "configs"
    base_output_dir = tmp_path / "output"
    standard_template_path = tmp_path / "templates" / "standard_design_template.fsf"
    custom_template_path = tmp_path / "templates" / "custom_design_template.fsf"

    # Create directories
    os.makedirs(preprocessing_dir / "sub-001" / "ses-001" / "func", exist_ok=True)
    os.makedirs(preprocessing_dir / "sub-001" / "ses-001" / "anat", exist_ok=True)
    os.makedirs(parameter_files_root / "sub-001", exist_ok=True)
    os.makedirs(custom_config_dir, exist_ok=True)
    os.makedirs(standard_template_path.parent, exist_ok=True)

    # Create mock files
    (preprocessing_dir / "sub-001" / "ses-001" / "func" / "sub-001_task-test_bold_run-1_synthstrip.nii.gz").write_text("dummy data")
    (preprocessing_dir / "sub-001" / "ses-001" / "anat" / "sub-001_T1w_synthstrip.nii.gz").write_text("dummy data")
    (parameter_files_root / "sub-001" / "sub-001_task-test_bold_run-1_configuration.md").write_text(
        "TOTAL_REPETITION_TIME=2.0\nTOTAL_FRAMES=150\nDISCARD_FRAMES=2\n"
        "CRITICAL_Z=2.3\nSMOOTHING_KERNEL=4\nPROB_THRESHOLD=0.05\nZ_THRESHOLD=3.1\nZ_MINIMUM=3.1\n"
    )
    (custom_config_dir / "custom_config.txt").write_text("Custom config content")
    standard_template_path.write_text("Template for standard design")
    custom_template_path.write_text("Template for custom design")

    return {
        "preprocessing_dir": str(preprocessing_dir),
        "design_files_dir": str(design_files_dir),
        "parameter_files_root": str(parameter_files_root),
        "custom_config_dir": str(custom_config_dir),
        "base_output_dir": str(base_output_dir),
        "standard_template_path": str(standard_template_path),
        "custom_template_path": str(custom_template_path),
    }

# Test the read_parameter_file function
def test_read_parameter_file(mock_file_structure):
    param_file = os.path.join(mock_file_structure["parameter_files_root"], "sub-001", "sub-001_task-test_bold_run-1_configuration.md")
    params = generate_design_files.read_parameter_file(param_file)
    assert params["TOTAL_REPETITION_TIME"] == "2.0"
    assert params["TOTAL_FRAMES"] == "150"
    assert params["Z_THRESHOLD"] == "3.1"

# Test the process_scan function
def test_process_scan(mock_file_structure):
    mock_data = mock_file_structure

    with patch("utils.generate_design_files.load_template", return_value=Template("Dummy template {{ OUTPUT_DIRECTORY }}")) as mock_template:
        with patch("utils.generate_design_files.read_parameter_file") as mock_read_params:
            mock_read_params.return_value = {
                "TOTAL_REPETITION_TIME": "2.0",
                "TOTAL_FRAMES": "150",
                "DISCARD_FRAMES": "2",
                "CRITICAL_Z": "2.3",
                "SMOOTHING_KERNEL": "4",
                "PROB_THRESHOLD": "0.05",
                "Z_THRESHOLD": "3.1",
                "Z_MINIMUM": "3.1",
            }

            generate_design_files.main(
                mock_data["preprocessing_dir"],
                mock_data["design_files_dir"],
                mock_data["parameter_files_root"],
                mock_data["custom_config_dir"],
                mock_data["standard_template_path"],
                mock_data["custom_template_path"],
                mock_data["base_output_dir"],
            )

            # Verify that design files are created
            expected_file = os.path.join(mock_data["design_files_dir"], "sub-001_task-test_run-1_bold_design-standard.fsf")
            assert os.path.exists(expected_file)

# Test handling missing configuration files
def test_missing_parameter_file(mock_file_structure):
    mock_data = mock_file_structure

    # Remove the parameter file to simulate a missing configuration
    param_file = os.path.join(mock_data["parameter_files_root"], "sub-001", "sub-001_task-test_bold_run-1_configuration.md")
    os.remove(param_file)

    with patch("utils.generate_design_files.read_parameter_file") as mock_read_params:
        generate_design_files.main(
            mock_data["preprocessing_dir"],
            mock_data["design_files_dir"],
            mock_data["parameter_files_root"],
            mock_data["custom_config_dir"],
            mock_data["standard_template_path"],
            mock_data["custom_template_path"],
            mock_data["base_output_dir"],
        )
        mock_read_params.assert_not_called()

# Test non-matching functional files
def test_non_matching_functional_file(mock_file_structure):
    mock_data = mock_file_structure

    # Rename functional file to an invalid name
    func_file = os.path.join(mock_data["preprocessing_dir"], "sub-001", "ses-001", "func", "invalid_name.nii.gz")
    os.rename(
        os.path.join(mock_data["preprocessing_dir"], "sub-001", "ses-001", "func", "sub-001_task-test_bold_run-1_synthstrip.nii.gz"),
        func_file,
    )

    with patch("utils.generate_design_files.process_scan") as mock_process:
        generate_design_files.main(
            mock_data["preprocessing_dir"],
            mock_data["design_files_dir"],
            mock_data["parameter_files_root"],
            mock_data["custom_config_dir"],
            mock_data["standard_template_path"],
            mock_data["custom_template_path"],
            mock_data["base_output_dir"],
        )
        mock_process.assert_not_called()
