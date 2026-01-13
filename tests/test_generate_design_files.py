import os
from unittest.mock import patch

from utils import generate_design_files


def write_config(config_path):
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        f.write(
            "TOTAL_REPETITION_TIME = 2.0\n"
            "TOTAL_FRAMES = 150\n"
            "DISCARD_FRAMES = 2\n"
            "CRITICAL_Z = 2.3\n"
            "SMOOTHING_KERNEL = 4\n"
            "PROB_THRESHOLD = 0.05\n"
            "Z_THRESHOLD = 3.1\n"
            "Z_MINIMUM = 3.1\n"
        )


def write_template(template_path):
    os.makedirs(os.path.dirname(template_path), exist_ok=True)
    with open(template_path, "w") as f:
        f.write(
            "set fmri(outputdir) {{ OUTPUT_DIRECTORY }}\n"
            "set fmri(tr) {{ TOTAL_REPETITION_TIME }}\n"
            "set fmri(npts) {{ TOTAL_FRAMES }}\n"
            "set fmri(ndelete) {{ DISCARD_FRAMES }}\n"
            "set fmri(custom) {{ CUSTOM_DESIGN_FILE }}\n"
        )


def test_main_generates_fsf(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    template_path = tmp_path / "templates" / "standard_design_template.fsf"
    os.makedirs(input_dir / "sub-001" / "ses-001" / "func", exist_ok=True)

    (input_dir / "sub-001" / "ses-001" / "func" / "sub-001_ses-001_task-hand_run-01_bold.nii.gz").write_text("dummy")

    config_path = output_dir / "fsl_feat_v6.0.7.4" / "configurations" / "sub-001" / "ses-001" / "sub-001_ses-001_task-hand_run-01_configuration.md"
    write_config(config_path)
    write_template(template_path)

    with patch("utils.generate_design_files.subprocess.run") as mock_run:
        generate_design_files.main(
            fsf_template=str(template_path),
            output_directory=str(output_dir),
            input_directory=str(input_dir),
            task="hand",
            custom_block=[],
            subjects=None,
            runs=[1],
            space="native",
        )

        output_fsf = output_dir / "fsl_feat_v6.0.7.4" / "subject_designs" / "space-native" / "sub-001_ses-001_task-hand_run-01.fsf"
        assert output_fsf.exists()
        mock_run.assert_called_once_with(["feat", str(output_fsf)], check=True)


def test_main_skips_missing_config(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    template_path = tmp_path / "templates" / "standard_design_template.fsf"
    os.makedirs(input_dir / "sub-001" / "ses-001" / "func", exist_ok=True)

    (input_dir / "sub-001" / "ses-001" / "func" / "sub-001_ses-001_task-hand_run-01_bold.nii.gz").write_text("dummy")
    write_template(template_path)

    with patch("utils.generate_design_files.subprocess.run") as mock_run:
        generate_design_files.main(
            fsf_template=str(template_path),
            output_directory=str(output_dir),
            input_directory=str(input_dir),
            task="hand",
            custom_block=[],
            subjects=None,
            runs=[1],
            space="native",
        )
        mock_run.assert_not_called()
