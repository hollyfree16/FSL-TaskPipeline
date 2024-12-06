import os
import pytest
from unittest.mock import patch, MagicMock
from utils import run_motion_outliers


@pytest.fixture
def mock_file_structure(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    os.makedirs(input_dir / "sub-001" / "func", exist_ok=True)
    os.makedirs(input_dir / "sub-002" / "func", exist_ok=True)

    # Create dummy .nii.gz files
    (input_dir / "sub-001" / "func" / "sub-001_task-rest_bold.nii.gz").write_text("dummy data")
    (input_dir / "sub-002" / "func" / "sub-002_task-rest_bold.nii.gz").write_text("dummy data")

    return str(input_dir), str(output_dir)


def test_process_file(mock_file_structure):
    input_dir, output_dir = mock_file_structure
    input_file = os.path.join(input_dir, "sub-001", "func", "sub-001_task-rest_bold.nii.gz")
    output_file = os.path.join(output_dir, "sub-001", "func", "sub-001_task-rest_confounds.txt")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with patch("utils.run_motion_outliers.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        run_motion_outliers.process_file(input_file, output_file)
        mock_run.assert_called_once_with(
            f"fsl_motion_outliers -i {input_file} -o {output_file} --dummy=2 -v --dvars",
            shell=True,
            check=True,
        )

def test_main(mock_file_structure):
    input_dir, output_dir = mock_file_structure

    with patch("utils.run_motion_outliers.process_file") as mock_process:
        mock_process.return_value = None
        run_motion_outliers.main(input_dir, output_dir, max_workers=2)
        assert mock_process.call_count == 2  # Two input files


def test_skip_existing_output(mock_file_structure):
    input_dir, output_dir = mock_file_structure
    input_file = os.path.join(input_dir, "sub-001", "func", "sub-001_task-rest_bold.nii.gz")
    output_file = os.path.join(output_dir, "sub-001", "func", "sub-001_task-rest_confounds.txt")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        f.write("existing output")

    with patch("utils.run_motion_outliers.subprocess.run") as mock_run:
        run_motion_outliers.process_file(input_file, output_file)
        mock_run.assert_not_called()  # Should skip since the output exists
