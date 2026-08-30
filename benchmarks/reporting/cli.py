"""Utility commands for benchmark records, rendering, and repeatability."""

import argparse
import json
from pathlib import Path

from benchmarks.longmemeval_v1.run import compare_runs

from .environment import validate_environment_reference
from .records import (
    load_record,
    normalized_artifact_sha256,
    record_from_artifacts,
    retrieval_result_sha256,
    validate_output_path,
    write_json,
)
from .render import render_record


def _validate(args: argparse.Namespace) -> None:
    record = load_record(args.record)
    if args.markdown:
        expected = render_record(record)
        actual = args.markdown.read_text(encoding="utf-8")
        if actual != expected:
            raise SystemExit(
                f"baseline Markdown mismatch: regenerate {args.markdown} from {args.record}"
            )
    print(f"valid benchmark record: {record['record_id']}")


def _render(args: argparse.Namespace) -> None:
    record = load_record(args.record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_record(record), encoding="utf-8")


def _record(args: argparse.Namespace) -> None:
    record = record_from_artifacts(
        args.artifact_dir,
        record_id=args.record_id,
        issue=args.issue,
        pull_request=args.pull_request,
        decision=args.decision,
        parent_record_id=args.parent_record_id,
        parent_commit=args.parent_commit,
        merge_commit=args.merge_commit,
        repeat_directory=args.repeat_artifact_dir,
        execution_role=args.execution_role,
        event_name=args.event_name,
        event_identity=args.event_identity,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        constraints_path=args.constraints,
    )
    write_json(args.output, record)
    if not record["determinism"]["equivalent"]:
        raise SystemExit("candidate repeated runs are not equivalent")


def _repeatability(args: argparse.Namespace) -> None:
    equivalent = compare_runs(args.first, args.second)
    first_normalized = normalized_artifact_sha256(args.first)
    second_normalized = normalized_artifact_sha256(args.second)
    first_retrieval = retrieval_result_sha256(args.first)
    second_retrieval = retrieval_result_sha256(args.second)
    payload = {
        "equivalent": equivalent,
        "first_normalized_sha256": first_normalized,
        "second_normalized_sha256": second_normalized,
        "first_retrieval_result_sha256": first_retrieval,
        "second_retrieval_result_sha256": second_retrieval,
        "retrieval_result_equivalent": first_retrieval == second_retrieval,
    }
    write_json(args.output, payload)
    print(json.dumps(payload, sort_keys=True))
    if not equivalent or first_normalized != second_normalized or first_retrieval != second_retrieval:
        raise SystemExit("candidate repeated runs are not deterministic")


def _path(args: argparse.Namespace) -> None:
    print(validate_output_path(args.path, args.allowed_root))


def _environment(args: argparse.Namespace) -> None:
    record = load_record(args.record)
    reference = load_record(args.reference)
    result = validate_environment_reference(record, reference)
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate-record")
    validate.add_argument("--record", type=Path, required=True)
    validate.add_argument("--markdown", type=Path)
    validate.set_defaults(function=_validate)

    render = commands.add_parser("render-record")
    render.add_argument("--record", type=Path, required=True)
    render.add_argument("--output", type=Path, required=True)
    render.set_defaults(function=_render)

    record = commands.add_parser("record-from-artifacts")
    record.add_argument("--artifact-dir", type=Path, required=True)
    record.add_argument("--repeat-artifact-dir", type=Path)
    record.add_argument("--record-id", required=True)
    record.add_argument("--issue", type=int, required=True)
    record.add_argument("--pull-request", type=int, required=True)
    record.add_argument(
        "--decision", choices=("KEEP", "ITERATE", "REVERT", "DROP", "PENDING"),
        default="PENDING",
    )
    record.add_argument("--parent-record-id")
    record.add_argument("--parent-commit")
    record.add_argument("--merge-commit")
    record.add_argument(
        "--execution-role",
        choices=("candidate", "parent", "canonical", "forward", "local"),
        default="local",
    )
    record.add_argument(
        "--event-name",
        choices=("pull_request", "push", "schedule", "workflow_dispatch", "local"),
        default="local",
    )
    record.add_argument("--event-identity", default="local-unspecified")
    record.add_argument("--run-id")
    record.add_argument("--run-attempt", type=int)
    record.add_argument(
        "--constraints",
        type=Path,
        default=Path("benchmarks/longmemeval_v1/constraints-ci.txt"),
    )
    record.add_argument("--output", type=Path, required=True)
    record.set_defaults(function=_record)

    repeat = commands.add_parser("verify-repeatability")
    repeat.add_argument("--first", type=Path, required=True)
    repeat.add_argument("--second", type=Path, required=True)
    repeat.add_argument("--output", type=Path, required=True)
    repeat.set_defaults(function=_repeatability)

    path = commands.add_parser("validate-output-path")
    path.add_argument("--path", type=Path, required=True)
    path.add_argument("--allowed-root", type=Path, required=True)
    path.set_defaults(function=_path)

    environment = commands.add_parser("validate-environment")
    environment.add_argument("--record", type=Path, required=True)
    environment.add_argument("--reference", type=Path, required=True)
    environment.add_argument("--output", type=Path)
    environment.set_defaults(function=_environment)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
