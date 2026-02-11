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
    output_file = os.path.join(
        output_dir,
        "fsl_motion-outliers_v6.0.7.4",
        "sub-001",
        "func",
        "sub-001_task-rest_confounds.txt",
    )
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # run_cmd delegates to utils.command.subprocess.run
    with patch("utils.command.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        run_motion_outliers.process_file(input_file, output_file, {"dummy_scan_rules": [], "default_dummy": 2})
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == [
            "fsl_motion_outliers",
            "-i",
            input_file,
            "-o",
            output_file,
            "--dummy=2",
            "-v",
            "--dvars",
        ]
        assert kwargs.get("check") is True

def test_main(mock_file_structure):
    input_dir, output_dir = mock_file_structure

    with patch("utils.run_motion_outliers.process_file") as mock_process:
        mock_process.return_value = None
        run_motion_outliers.main(input_dir, output_dir, None, max_workers=2)
        assert mock_process.call_count == 2  # Two input files


def test_skip_existing_output(mock_file_structure):
    input_dir, output_dir = mock_file_structure
    input_file = os.path.join(input_dir, "sub-001", "func", "sub-001_task-rest_bold.nii.gz")
    output_file = os.path.join(
        output_dir,
        "fsl_motion-outliers_v6.0.7.4",
        "sub-001",
        "func",
        "sub-001_task-rest_confounds.txt",
    )

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        f.write("existing output")

    with patch("utils.command.subprocess.run") as mock_run:
        run_motion_outliers.process_file(input_file, output_file, {"dummy_scan_rules": [], "default_dummy": 2})
        mock_run.assert_not_called()  # Should skip since the output exists


def test_main_propagates_worker_exceptions(mock_file_structure):
    input_dir, output_dir = mock_file_structure

    with patch("utils.run_motion_outliers.process_file", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="boom"):
            run_motion_outliers.main(input_dir, output_dir, None, max_workers=2)
