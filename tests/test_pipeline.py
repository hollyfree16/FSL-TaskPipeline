import sys
from unittest.mock import patch

import pytest

import run_pipeline


def test_run_pipeline_multiple_subjects_multiple_tasks(tmp_path):
    # Arrange CLI args
    mock_args = [
        "run_pipeline.py",
        "--input_directory", str(tmp_path / "input"),
        "--output_directory", str(tmp_path / "output"),
        "--fsf_template", "configuration_templates/standard_design_template.fsf",
        "--higher_level_fsf_template", "configuration_templates/higher_level_feat_design_template.fsf",
        "--task", "hand", "language", "rest",
        "--run", "1", "2",
        "--subjects", "sub-001", "sub-002",
    ]

    def fake_generate_design_files_main(*, fsf_template, output_directory, input_directory, task, custom_block, subjects, runs):
        # subjects is a single subject id (string) per sequential processing
        assert subjects in {"sub-001", "sub-002"}
        return [f"/tmp/{subjects}_ses-001_task-{task}_runs-01-02.fsf"]

    def fake_generate_higher_level_feat_files_main(*, input_directory, template_file, design_output_dir, feat_output_dir, run_pair, subjects, task_filters):
        # subjects is passed through so higher-level can filter
        assert subjects in {"sub-001", "sub-002"}
        assert set(task_filters) == {"hand", "language", "rest"}
        return [f"/tmp/higher_{subjects}_runs-01-02.fsf"]

    with patch.object(sys, "argv", mock_args),          patch("run_pipeline.run_motion_outliers_main") as mock_motion,          patch("run_pipeline.run_synthstrip_main") as mock_synthstrip,          patch("run_pipeline.extract_parameters_main") as mock_extract,          patch("run_pipeline.generate_design_files_main", side_effect=fake_generate_design_files_main) as mock_design,          patch("run_pipeline.generate_higher_level_feat_files_main", side_effect=fake_generate_higher_level_feat_files_main) as mock_higher,          patch("run_pipeline.run_feat_main") as mock_run_feat:

        run_pipeline.main()

        # Preprocessing should run once per subject (not once per task)
        assert mock_motion.call_count == 2
        assert mock_synthstrip.call_count == 2
        assert mock_extract.call_count == 2

        called_subjects = [c.args[2] for c in mock_synthstrip.call_args_list]
        assert called_subjects == ["sub-001", "sub-002"]

        # Design generation should run per subject * per task
        assert mock_design.call_count == 2 * 3

        # First-level FEAT should be invoked once per subject with that subject's FSFs
        assert mock_run_feat.call_count == 4  # 1x first-level + 1x higher-level per subject
        first_level_calls = [mock_run_feat.call_args_list[0], mock_run_feat.call_args_list[2]]
        assert first_level_calls[0].args[0] == [
            "/tmp/sub-001_ses-001_task-hand_runs-01-02.fsf",
            "/tmp/sub-001_ses-001_task-language_runs-01-02.fsf",
            "/tmp/sub-001_ses-001_task-rest_runs-01-02.fsf",
        ]
        assert first_level_calls[1].args[0] == [
            "/tmp/sub-002_ses-001_task-hand_runs-01-02.fsf",
            "/tmp/sub-002_ses-001_task-language_runs-01-02.fsf",
            "/tmp/sub-002_ses-001_task-rest_runs-01-02.fsf",
        ]

        # Higher-level generation should be invoked once per subject
        assert mock_higher.call_count == 2


def test_run_pipeline_missing_args():
    with patch.object(sys, "argv", ["run_pipeline.py"]):
        with pytest.raises(SystemExit):
            run_pipeline.main()
