import os

from utils import generate_higher_level_feat_files


def write_template(template_path):
    os.makedirs(os.path.dirname(template_path), exist_ok=True)
    with open(template_path, "w") as f:
        f.write(
            "set fmri(outputdir) {{ OUTPUT_DIRECTORY }}\n"
            "set fmri(input1) {{ FEAT_DIRECTORY_RUN_1 }}\n"
            "set fmri(input2) {{ FEAT_DIRECTORY_RUN_2 }}\n"
        )


def test_generates_higher_level_fsf(tmp_path):
    input_dir = tmp_path / "first_level"
    design_output_dir = tmp_path / "designs"
    feat_output_dir = tmp_path / "higher_level"
    template_path = tmp_path / "templates" / "higher_level.fsf"

    run_01 = input_dir / "sub-001" / "ses-001" / "sub-001_ses-001_task-hand_run-01"
    run_02 = input_dir / "sub-001" / "ses-001" / "sub-001_ses-001_task-hand_run-02"
    os.makedirs(run_01, exist_ok=True)
    os.makedirs(run_02, exist_ok=True)
    write_template(template_path)

    generate_higher_level_feat_files.main(
        input_directory=str(input_dir),
        template_file=str(template_path),
        design_output_dir=str(design_output_dir),
        feat_output_dir=str(feat_output_dir),
        run_pair=(1, 2),
    )

    expected_fsf = design_output_dir / "sub-001" / "ses-001" / "sub-001_ses-001_task-hand_runs-01-02.fsf"
    assert expected_fsf.exists()
    content = expected_fsf.read_text()
    assert str(run_01) in content
    assert str(run_02) in content


def test_skips_when_missing_pair(tmp_path):
    input_dir = tmp_path / "first_level"
    design_output_dir = tmp_path / "designs"
    feat_output_dir = tmp_path / "higher_level"
    template_path = tmp_path / "templates" / "higher_level.fsf"

    run_01 = input_dir / "sub-001" / "ses-001" / "sub-001_ses-001_task-hand_run-01"
    os.makedirs(run_01, exist_ok=True)
    write_template(template_path)

    generate_higher_level_feat_files.main(
        input_directory=str(input_dir),
        template_file=str(template_path),
        design_output_dir=str(design_output_dir),
        feat_output_dir=str(feat_output_dir),
        run_pair=(1, 2),
    )

    expected_fsf = design_output_dir / "sub-001" / "ses-001" / "sub-001_ses-001_task-hand_runs-01-02.fsf"
    assert not expected_fsf.exists()


def test_higher_level_filters_subjects_and_tasks(tmp_path):
    input_dir = tmp_path / "first_level"
    design_output_dir = tmp_path / "designs"
    feat_output_dir = tmp_path / "higher_level"
    template_path = tmp_path / "templates" / "higher_level.fsf"

    # sub-001 has hand runs 1/2
    run_01 = input_dir / "sub-001" / "ses-001" / "sub-001_ses-001_task-hand_run-01"
    run_02 = input_dir / "sub-001" / "ses-001" / "sub-001_ses-001_task-hand_run-02"
    os.makedirs(run_01, exist_ok=True)
    os.makedirs(run_02, exist_ok=True)

    # sub-002 has rest runs 1/2
    run_01_b = input_dir / "sub-002" / "ses-001" / "sub-002_ses-001_task-rest_run-01"
    run_02_b = input_dir / "sub-002" / "ses-001" / "sub-002_ses-001_task-rest_run-02"
    os.makedirs(run_01_b, exist_ok=True)
    os.makedirs(run_02_b, exist_ok=True)

    write_template(template_path)

    # Filter to only sub-001 and only task hand
    generate_higher_level_feat_files.main(
        input_directory=str(input_dir),
        template_file=str(template_path),
        design_output_dir=str(design_output_dir),
        feat_output_dir=str(feat_output_dir),
        run_pair=(1, 2),
        subjects=["sub-001"],
        task_filters=["hand"],
    )

    expected_fsf_sub1 = design_output_dir / "sub-001" / "ses-001" / "sub-001_ses-001_task-hand_runs-01-02.fsf"
    expected_fsf_sub2 = design_output_dir / "sub-002" / "ses-001" / "sub-002_ses-001_task-rest_runs-01-02.fsf"
    assert expected_fsf_sub1.exists()
    assert not expected_fsf_sub2.exists()
