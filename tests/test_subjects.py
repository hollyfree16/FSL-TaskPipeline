from utils.subjects import parse_subjects_arg


def test_parse_subjects_arg_from_list():
    assert parse_subjects_arg(["sub-001", " sub-002 "]) == ["sub-001", "sub-002"]


def test_parse_subjects_arg_from_comma_string():
    assert parse_subjects_arg("sub-001, sub-002") == ["sub-001", "sub-002"]


def test_parse_subjects_arg_from_file(tmp_path):
    f = tmp_path / "subjects.txt"
    f.write_text("sub-001\nsub-002,sub-003\n")

    assert parse_subjects_arg(str(f)) == ["sub-001", "sub-002", "sub-003"]


def test_parse_subjects_arg_empty_returns_none():
    assert parse_subjects_arg(None) is None
    assert parse_subjects_arg([]) is None
