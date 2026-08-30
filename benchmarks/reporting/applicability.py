"""Parse and validate the PR benchmark-applicability declaration safely."""

import argparse
import os
import re
from pathlib import Path
from typing import Dict


LEVELS = {"REQUIRED", "SMOKE_ONLY", "NOT_APPLICABLE"}
DECLARATION_RE = re.compile(
    r"^\s*Benchmark applicability:\s*`?(REQUIRED|SMOKE_ONLY|NOT_APPLICABLE)`?\s*$",
    re.MULTILINE,
)
RATIONALE_RE = re.compile(r"^\s*Benchmark rationale:\s*(.+?)\s*$", re.MULTILINE)


def parse_applicability(body: str) -> Dict[str, str]:
    if not isinstance(body, str):
        raise ValueError("PR body must be text")
    if len(body.encode("utf-8")) > 1_000_000:
        raise ValueError("PR body exceeds the 1 MB applicability parsing limit")
    if "\x00" in body:
        raise ValueError("PR body contains a NUL byte")
    declarations = DECLARATION_RE.findall(body)
    if not declarations:
        raise ValueError(
            "missing benchmark applicability declaration; add exactly one line: "
            "Benchmark applicability: REQUIRED|SMOKE_ONLY|NOT_APPLICABLE"
        )
    if len(declarations) != 1:
        raise ValueError(
            f"multiple benchmark applicability declarations found: {len(declarations)}"
        )
    level = declarations[0]
    if level not in LEVELS:  # defensive; the regular expression is authoritative
        raise ValueError(f"unsupported benchmark applicability: {level!r}")
    rationales = RATIONALE_RE.findall(body)
    rationale = rationales[-1].strip() if rationales else ""
    if level in {"SMOKE_ONLY", "NOT_APPLICABLE"} and not rationale:
        raise ValueError(f"Benchmark rationale is required for {level}")
    return {"applicability": level, "rationale": rationale}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--body-file", type=Path)
    source.add_argument("--body-env")
    parser.add_argument("--github-output", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    body = (
        args.body_file.read_text(encoding="utf-8")
        if args.body_file is not None
        else os.environ.get(args.body_env, "")
    )
    parsed = parse_applicability(body)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as handle:
            handle.write(f"applicability={parsed['applicability']}\n")
    print(parsed["applicability"])


if __name__ == "__main__":
    main()
