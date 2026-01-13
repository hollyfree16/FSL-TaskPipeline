import pytest
import sys
from unittest.mock import patch, MagicMock
import run_pipeline
import os

# Test the main function of the wrapper
def test_run_pipeline_main(tmp_path):
    # Mock arguments for the pipeline script
    mock_args = [
        "--input_directory", str(tmp_path / "input"),
        "--output_directory", str(tmp_path / "output"),
        "--fsf_template", "configuration_templates/standard_design_template.fsf",
        "--task", "hand",
        "--run", "1", "2",
        "--higher_level_fsf_template", "configuration_templates/higher_level_feat_design_template.fsf",
    ]

    with patch.object(sys, "argv", ["run_pipeline.py"] + mock_args):
        # Mock the main functions of each utility script
        with patch("run_pipeline.run_motion_outliers_main", autospec=True) as mock_motion_outliers, \
             patch("run_pipeline.run_synthstrip_main", autospec=True) as mock_synthstrip, \
             patch("run_pipeline.extract_parameters_main", autospec=True) as mock_extract_parameters, \
             patch("run_pipeline.generate_design_files_main", autospec=True) as mock_generate_design_files, \
             patch("run_pipeline.generate_higher_level_feat_files_main", autospec=True) as mock_higher_level:

            # Call the main function
            run_pipeline.main()

            # Verify each utility function is called with the correct arguments
            mock_motion_outliers.assert_called_once_with(
                str(tmp_path / "input"),
                str(tmp_path / "output"),
                None,
                10,
                "hand",
                [1, 2],
            )
            mock_synthstrip.assert_called_once_with(
                str(tmp_path / "input"),
                str(tmp_path / "output"),
                None,
                10,
                "hand",
                [1, 2],
            )
            mock_extract_parameters.assert_called_once_with(
                str(tmp_path / "input"),
                str(tmp_path / "output"),
                None,
                "hand",
                [1, 2],
            )
            mock_generate_design_files.assert_called_once_with(
                fsf_template="configuration_templates/standard_design_template.fsf",
                output_directory=str(tmp_path / "output"),
                input_directory=str(tmp_path / "input"),
                task="hand",
                custom_block=[],
                subjects=None,
                runs=[1, 2],
                space="native",
            )
            mock_higher_level.assert_called_once_with(
                input_directory=os.path.join(
                    str(tmp_path / "output"),
                    "fsl_feat_v6.0.7.4",
                    "standard",
                    "space-native",
                ),
                template_file="configuration_templates/higher_level_feat_design_template.fsf",
                design_output_dir=os.path.join(
                    str(tmp_path / "output"),
                    "fsl_feat_v6.0.7.4",
                    "higher_level_designs",
                    "standard",
                    "space-mni",
                ),
                feat_output_dir=os.path.join(
                    str(tmp_path / "output"),
                    "fsl_feat_v6.0.7.4",
                    "higher_level_outputs",
                    "standard",
                    "space-mni",
                ),
                run_pair=(1, 2),
            )

# Test for missing arguments
def test_run_pipeline_missing_args():
    with patch.object(sys, "argv", ["run_pipeline.py"]):  # No arguments provided
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            run_pipeline.main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code != 0  # Expect non-zero exit code for missing args
