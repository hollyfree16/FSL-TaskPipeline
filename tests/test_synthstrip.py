import os
import pytest
from unittest.mock import patch, MagicMock
from utils import run_synthstrip  # Updated for the project's directory structure

# Helper function to create a mock directory structure
@pytest.fixture
def mock_file_structure(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    os.makedirs(input_dir / "sub-001" / "ses-001" / "anat", exist_ok=True)
    os.makedirs(input_dir / "sub-002" / "ses-001" / "anat", exist_ok=True)

    # Create dummy .nii.gz files
    (input_dir / "sub-001" / "ses-001" / "anat" / "sub-001_ses-001_T1w.nii.gz").write_text("dummy data")
    (input_dir / "sub-002" / "ses-001" / "anat" / "sub-002_ses-001_T1w.nii.gz").write_text("dummy data")

    return str(input_dir), str(output_dir)

# Test the check_dependencies function
def test_check_dependencies():
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/path/to/mri_synthstrip"
        run_synthstrip.check_dependencies()
        mock_which.assert_called_once_with("mri_synthstrip")

    with patch("shutil.which", return_value=None):
        with patch("sys.exit") as mock_exit:
            run_synthstrip.check_dependencies()
            mock_exit.assert_called_once_with(1)

# Test the process_file function
def test_process_file(mock_file_structure):
    input_dir, output_dir = mock_file_structure
    input_file = os.path.join(input_dir, "sub-001", "ses-001", "anat", "sub-001_ses-001_T1w.nii.gz")
    output_file = os.path.join(
        output_dir,
        "freesurfer_synthstrip_v8.1.0",
        "sub-001",
        "ses-001",
        "anat",
        "sub-001_ses-001_T1w_synthstrip.nii.gz",
    )
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with patch("utils.run_synthstrip.subprocess.run") as mock_run, \
         patch("utils.run_synthstrip.nib.load") as mock_load:
        mock_img = MagicMock()
        mock_img.shape = (64, 64, 33)
        mock_load.return_value = mock_img
        mock_run.return_value = MagicMock()
        run_synthstrip.process_file(input_file, input_dir, output_dir)
        mock_run.assert_called_once_with(
            f'mri_synthstrip -i "{input_file}" -o "{output_file}"',
            shell=True,
            check=True,
        )

# Test the gather_nifti_files function
def test_gather_nifti_files(mock_file_structure):
    input_dir, _ = mock_file_structure
    files = run_synthstrip.gather_nifti_files(input_dir)
    assert len(files) == 2  # Two .nii.gz files
    assert files[0].endswith("sub-001_ses-001_T1w.nii.gz")
    assert files[1].endswith("sub-002_ses-001_T1w.nii.gz")

# Test the main function
def test_main(mock_file_structure):
    input_dir, output_dir = mock_file_structure

    with patch("utils.run_synthstrip.process_file") as mock_process, \
         patch("utils.run_synthstrip.check_dependencies") as mock_check:
        mock_process.return_value = None
        mock_check.return_value = None
        run_synthstrip.main(input_dir, output_dir, None, max_workers=2)
        assert mock_process.call_count == 2  # Two input files
        mock_check.assert_called_once()

# Test skipping existing output
def test_skip_existing_output(mock_file_structure):
    input_dir, output_dir = mock_file_structure
    input_file = os.path.join(input_dir, "sub-001", "ses-001", "anat", "sub-001_ses-001_T1w.nii.gz")
    output_file = os.path.join(
        output_dir,
        "freesurfer_synthstrip_v8.1.0",
        "sub-001",
        "ses-001",
        "anat",
        "sub-001_ses-001_T1w_synthstrip.nii.gz",
    )

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        f.write("existing output")

    with patch("utils.run_synthstrip.subprocess.run") as mock_run:
        run_synthstrip.process_file(input_file, input_dir, output_dir)
        mock_run.assert_not_called()  # Should skip since the output exists
