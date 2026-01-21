import argparse
import logging
import os
import re
from jinja2 import Template

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

FEAT_DIR_PATTERN = re.compile(
    r"^(?P<subject>sub-[^_]+)_(?P<session>ses-[^_]+)_task-(?P<task>[^_]+)_run-(?P<run>\d+)"
)


def parse_feat_dir_name(directory_name):
    match = FEAT_DIR_PATTERN.match(directory_name)
    if not match:
        return None
    return {
        "subject": match.group("subject"),
        "session": match.group("session"),
        "task": match.group("task"),
        "run": int(match.group("run")),
    }


def _normalize_subjects(subjects):
    if not subjects:
        return None
    if isinstance(subjects, str):
        # allow comma-separated
        subs=[s.strip() for s in subjects.split(',') if s.strip()]
        return set(subs) if subs else None
    return set(subjects)


def collect_feat_dirs(input_directory, *, subjects=None, task_filters=None):
    entries = []
    if not os.path.isdir(input_directory):
        logging.warning("Input directory not found: %s", input_directory)
        return entries

    for root, dirs, _ in os.walk(input_directory):
        for directory in dirs:
            info = parse_feat_dir_name(directory)
            if not info:
                continue
            subject_set = _normalize_subjects(subjects)
            if subject_set is not None and info.get('subject') not in subject_set:
                continue
            if task_filters and info.get('task') not in set(task_filters):
                continue
            entries.append(
                {
                    "path": os.path.join(root, directory),
                    **info,
                }
            )
    return entries


def pair_runs(entries, run_pair):
    grouped = {}
    for entry in entries:
        key = (entry["subject"], entry["session"], entry["task"])
        grouped.setdefault(key, {})[entry["run"]] = entry["path"]

    pairs = []
    run_a, run_b = run_pair
    for key, runs in grouped.items():
        if run_a in runs and run_b in runs:
            pairs.append(
                {
                    "subject": key[0],
                    "session": key[1],
                    "task": key[2],
                    "run_a": run_a,
                    "run_b": run_b,
                    "path_a": runs[run_a],
                    "path_b": runs[run_b],
                }
            )
        else:
            missing = [str(r) for r in (run_a, run_b) if r not in runs]
            logging.info(
                "Skipping pair for %s %s task-%s, missing runs: %s",
                key[0],
                key[1],
                key[2],
                ", ".join(missing),
            )
    return pairs


def render_fsf(template_file, output_directory, feat_dir_a, feat_dir_b):
    with open(template_file, "r") as template:
        template_content = template.read()

    jinja_template = Template(template_content)
    return jinja_template.render(
        OUTPUT_DIRECTORY=output_directory,
        FEAT_DIRECTORY_RUN_1=feat_dir_a,
        FEAT_DIRECTORY_RUN_2=feat_dir_b,
    )


def write_fsf(output_fsf, rendered_content):
    os.makedirs(os.path.dirname(output_fsf), exist_ok=True)
    with open(output_fsf, "w") as output:
        output.write(rendered_content)


def main(input_directory, template_file, design_output_dir, feat_output_dir, run_pair=(1, 2), *, subjects=None, task_filters=None):
    """Generate higher-level FSF files.

    Returns a list of generated FSF paths (existing FSFs are not included).
    """
    generated_fsfs = []
    entries = collect_feat_dirs(input_directory, subjects=subjects, task_filters=task_filters)
    if not entries:
        logging.info("No FEAT directories found. Exiting.")
        return generated_fsfs

    pairs = pair_runs(entries, run_pair)
    if not pairs:
        logging.info("No run pairs found to process. Exiting.")
        return generated_fsfs

    for pair in pairs:
        output_base = (
            f"{pair['subject']}_{pair['session']}_task-{pair['task']}"
            f"_runs-{pair['run_a']:02d}-{pair['run_b']:02d}"
        )
        output_feat_dir = os.path.join(
            feat_output_dir, pair["subject"], pair["session"], output_base
        )
        output_fsf = os.path.join(
            design_output_dir, pair["subject"], pair["session"], f"{output_base}.fsf"
        )

        if os.path.exists(output_fsf):
            logging.info("FSF already exists, skipping: %s", output_fsf)
            continue

        rendered_content = render_fsf(
            template_file=template_file,
            output_directory=output_feat_dir,
            feat_dir_a=pair["path_a"],
            feat_dir_b=pair["path_b"],
        )
        write_fsf(output_fsf, rendered_content)
        logging.info("Generated higher-level FSF: %s", output_fsf)
        generated_fsfs.append(output_fsf)

    return generated_fsfs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate higher-level FEAT design files from first-level outputs."
    )
    parser.add_argument("--input_directory", required=True, help="Base directory for first-level FEAT outputs.")
    parser.add_argument("--template_file", required=True, help="Path to the higher-level .fsf template file.")
    parser.add_argument("--design_output_dir", required=True, help="Output directory for higher-level FSF files.")
    parser.add_argument("--feat_output_dir", required=True, help="Output directory for higher-level FEAT outputs.")
    parser.add_argument("--run_pair", nargs=2, type=int, default=[1, 2], help="Run numbers to pair (default: 1 2).")
    parser.add_argument("--subjects", nargs="+", required=False, help="Optional subject IDs to include (space- or comma-separated).")
    parser.add_argument("--task", nargs="+", required=False, help="Optional task names to include.")
    args = parser.parse_args()

    main(
        input_directory=args.input_directory,
        template_file=args.template_file,
        design_output_dir=args.design_output_dir,
        feat_output_dir=args.feat_output_dir,
        run_pair=tuple(args.run_pair),
        subjects=args.subjects,
        task_filters=args.task,
    )
