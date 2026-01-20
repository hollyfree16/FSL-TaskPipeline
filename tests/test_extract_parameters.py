import os
import pytest
from unittest.mock import patch, MagicMock
from utils import extract_parameters  # Update based on your directory structure

# Fixture to create a mock directory structure
@pytest.fixture
def mock_file_structure(tmp_path):
    base_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    os.makedirs(base_dir / "sub-001" / "ses-001" / "func", exist_ok=True)
    os.makedirs(base_dir / "sub-002" / "ses-002" / "func", exist_ok=True)

    # Create dummy .nii.gz files
    (base_dir / "sub-001" / "ses-001" / "func" / "sub-001_ses-001_task-rest_run-01_bold.nii.gz").write_text("dummy data")
    (base_dir / "sub-002" / "ses-002" / "func" / "sub-002_ses-002_task-rest_run-01_bold.nii.gz").write_text("dummy data")

    return str(base_dir), str(output_dir)

# Test the extract_and_write_scan_info function
def test_extract_and_write_scan_info(mock_file_structure):
    base_dir, output_dir = mock_file_structure

    # Mock nibabel's nib.load and header properties
    mock_nifti = MagicMock()
    mock_nifti.header.get_zooms.return_value = (2.0, 2.0, 2.0, 2.5)  # Dummy TR
    mock_nifti.shape = (64, 64, 33, 200)  # Dummy shape with 200 frames

    with patch.object(extract_parameters.nib, "load", return_value=mock_nifti):
        extract_parameters.extract_and_write_scan_info(base_dir, output_dir)

    # Check that configuration files are created correctly
    sub_001_config = os.path.join(
        output_dir,
        "fsl_feat_v6.0.7.4",
        "configurations",
        "sub-001",
        "ses-001",
        "sub-001_ses-001_task-rest_run-01_configuration.md",
    )
    sub_002_config = os.path.join(
        output_dir,
        "fsl_feat_v6.0.7.4",
        "configurations",
        "sub-002",
        "ses-002",
        "sub-002_ses-002_task-rest_run-01_configuration.md",
    )

    assert os.path.exists(sub_001_config)
    assert os.path.exists(sub_002_config)

    # Verify contents of one configuration file
    with open(sub_001_config, "r") as config_file:
        config_content = config_file.read()
        assert "TOTAL_REPETITION_TIME = 2.5" in config_content
        assert "TOTAL_FRAMES = 200" in config_content
        assert "DISCARD_FRAMES = 2" in config_content

# Test skipping existing configurations
def test_skip_existing_configuration(mock_file_structure):
    base_dir, output_dir = mock_file_structure
    sub_001_output_dir = os.path.join(
        output_dir, "fsl_feat_v6.0.7.4", "configurations", "sub-001", "ses-001"
    )
    os.makedirs(sub_001_output_dir, exist_ok=True)

    existing_config = os.path.join(
        sub_001_output_dir, "sub-001_ses-001_task-rest_run-01_configuration.md"
    )
    with open(existing_config, "w") as f:
        f.write("Existing content")

    with patch.object(extract_parameters.nib, "load") as mock_load:
        extract_parameters.extract_and_write_scan_info(base_dir, output_dir)

    # Ensure the existing configuration file was not overwritten
    with open(existing_config, "r") as config_file:
        assert "Existing content" in config_file.read()

# Test handling of non-NIfTI files
def test_non_nifti_files(mock_file_structure):
    base_dir, output_dir = mock_file_structure
    non_nifti_file = os.path.join(base_dir, "sub-001", "ses-001", "func", "random_file.txt")
    with open(non_nifti_file, "w") as f:
        f.write("dummy data")

    with patch.object(extract_parameters.nib, "load") as mock_load:
        extract_parameters.extract_and_write_scan_info(base_dir, output_dir)

    # Ensure non-NIfTI file was ignored and no additional configurations were created
    config_dir = os.path.join(
        output_dir, "fsl_feat_v6.0.7.4", "configurations", "sub-001", "ses-001"
    )
    assert os.path.exists(config_dir)
    assert len(os.listdir(config_dir)) == 1  # Only the valid .nii.gz file's config exists
