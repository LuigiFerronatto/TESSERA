"""Offline preparation commands only; no provider or full-500 execution path."""

import argparse
from pathlib import Path
from .common import canonical, read, write_new
from .judge import draft_packet, validate_draft_packet
from .preregistration import (draft_preregistration, execute, readiness_errors,
                             selection_from_dataset, validate_preregistration)
from .synthetic import oracle_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    synthetic = sub.add_parser("synthetic")
    synthetic.add_argument("--output", type=Path, required=True)
    ids = sub.add_parser("prepare-ids")
    ids.add_argument("--dataset", type=Path, required=True)
    ids.add_argument("--output", type=Path, required=True)
    draft = sub.add_parser("draft-preregistration")
    draft.add_argument("--selection", type=Path, required=True)
    draft.add_argument("--output", type=Path, required=True)
    packet = sub.add_parser("judge-packet")
    packet.add_argument("--output", type=Path, required=True)
    for name in ("validate", "execute"):
        command = sub.add_parser(name)
        command.add_argument("--selection", type=Path, required=True)
        command.add_argument("--preregistration", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "synthetic":
            print(canonical(oracle_run(args.output)))
        elif args.command == "prepare-ids":
            write_new(args.output, selection_from_dataset(args.dataset))
        elif args.command == "draft-preregistration":
            write_new(args.output, draft_preregistration(read(args.selection)))
        elif args.command == "judge-packet":
            value = draft_packet()
            validate_draft_packet(value)
            write_new(args.output, value)
        else:
            selection, prereg = read(args.selection), read(args.preregistration)
            if args.command == "execute":
                execute(prereg, selection)
            validate_preregistration(prereg, selection)
            print(canonical({"structurally_valid": True, "execution_available": False,
                             "remaining_gates": readiness_errors(prereg, selection)}))
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"blocked: {exc}\n")


if __name__ == "__main__":
    main()
